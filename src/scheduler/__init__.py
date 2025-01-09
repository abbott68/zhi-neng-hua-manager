from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from src.models import Task, db, MonitorData, ProcessData, TaskExecution, AnalysisReport
import subprocess
import logging
from pytz import timezone
from sqlalchemy import inspect
from datetime import datetime, timedelta
import psutil
import time
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression
import matplotlib.pyplot as plt
import seaborn as sns
from flask import current_app

logger = logging.getLogger(__name__)

def init_scheduler(app):
    """初始化调度器"""
    # 配置执行器
    executors = {
        'default': ThreadPoolExecutor(20),
        'processpool': ProcessPoolExecutor(5)
    }
    
    # 配置任务存储
    job_defaults = {
        'coalesce': True,
        'max_instances': 3,
        'misfire_grace_time': 300
    }
    
    # 创建调度器
    scheduler = BackgroundScheduler(
        executors=executors,
        job_defaults=job_defaults,
        timezone=timezone(app.config.get('SCHEDULER_TIMEZONE', 'Asia/Shanghai'))
    )
    
    # 添加任务，使用闭包保存 app 实例
    def collect_metrics_job():
        with app.app_context():
            collect_metrics(app)
            
    def analyze_performance_job():
        with app.app_context():
            analyze_performance(app)
            
    def cleanup_old_data_job():
        with app.app_context():
            cleanup_old_data(app, retention_days=30)
            
    def predict_resource_usage_job():
        with app.app_context():
            predict_resource_usage(app)
    
    # 添加数据收集任务
    scheduler.add_job(
        func=collect_metrics_job,
        trigger='interval',
        minutes=5,
        id='collect_metrics',
        replace_existing=True
    )
    
    # 添加性能分析任务
    scheduler.add_job(
        func=analyze_performance_job,
        trigger='interval',
        minutes=30,
        id='analyze_performance',
        replace_existing=True
    )
    
    # 添加数据清理任务
    scheduler.add_job(
        func=cleanup_old_data_job,
        trigger='cron',
        hour=3,  # 每天凌晨3点执行
        id='cleanup_old_data',
        replace_existing=True
    )
    
    # 添加资源使用预测任务
    scheduler.add_job(
        func=predict_resource_usage_job,
        trigger='interval',
        hours=6,
        id='predict_resource_usage',
        replace_existing=True
    )
    
    # 添加任务执行监听器
    def job_listener(event):
        with app.app_context():
            job_executed_listener(event)
            
    scheduler.add_listener(
        job_listener,
        EVENT_JOB_EXECUTED | EVENT_JOB_ERROR
    )
    
    try:
        scheduler.start()
        logger.info("Scheduler started successfully")
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}")
    
    return scheduler

def job_executed_listener(event):
    """任务执行监听器"""
    try:
        job_id = event.job_id
        if not job_id:
            return
            
        execution_time = time.time() - event.scheduled_run_time.timestamp()
        success = not event.exception
        
        # 获取应用上下文
        app = current_app._get_current_object() if current_app else None
        if not app:
            logger.error("No application context available")
            return
            
        with app.app_context():
            # 记录任务执行情况
            task_execution = TaskExecution(
                job_id=job_id,
                scheduled_time=event.scheduled_run_time,
                start_time=event.scheduled_run_time,
                end_time=datetime.now(),
                execution_time=execution_time,
                success=success,
                error_message=str(event.exception) if event.exception else None
            )
            
            db.session.add(task_execution)
            db.session.commit()
            
            # 记录性能问题
            if execution_time > 5:  # 执行时间超过5秒
                logger.warning(f"Job {job_id} took {execution_time:.2f} seconds to complete")
                
    except Exception as e:
        logger.error(f"Error in job execution listener: {e}")

def collect_metrics(app):
    """收集系统指标"""
    try:
        # 收集CPU使用率
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_metric = MonitorData(type='cpu', metric='usage', value=cpu_percent)
        db.session.add(cpu_metric)
        
        # 收集内存使用率
        memory = psutil.virtual_memory()
        memory_metric = MonitorData(type='memory', metric='usage', value=memory.percent)
        db.session.add(memory_metric)
        
        # 收集磁盘使用率
        disk = psutil.disk_usage('/')
        disk_metric = MonitorData(type='disk', metric='usage', value=disk.percent)
        db.session.add(disk_metric)
        
        # 收集网络IO
        net = psutil.net_io_counters()
        net_sent = MonitorData(type='network', metric='bytes_sent', value=net.bytes_sent)
        net_recv = MonitorData(type='network', metric='bytes_recv', value=net.bytes_recv)
        db.session.add(net_sent)
        db.session.add(net_recv)
        
        # 收集进程信息
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                pinfo = proc.info
                process_data = ProcessData(
                    pid=pinfo['pid'],
                    name=pinfo['name'],
                    cpu_percent=pinfo['cpu_percent'],
                    memory_percent=pinfo['memory_percent']
                )
                db.session.add(process_data)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        db.session.commit()
        logger.info("Metrics collected successfully")
        
    except Exception as e:
        logger.error(f"Failed to collect metrics: {e}")
        db.session.rollback()

def cleanup_old_data(app, retention_days):
    """清理过期数据"""
    start_time = time.time()
    try:
        with app.app_context():
            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
            
            # 清理监控数据
            monitor_count = MonitorData.query.filter(
                MonitorData.timestamp < cutoff_date
            ).delete()
            
            # 清理进程数据
            process_count = ProcessData.query.filter(
                ProcessData.timestamp < cutoff_date
            ).delete()
            
            # 清理任务执行记录
            execution_count = TaskExecution.query.filter(
                TaskExecution.end_time < cutoff_date
            ).delete()
            
            db.session.commit()
            
            execution_time = time.time() - start_time
            logger.info(
                f"Cleaned up data older than {retention_days} days in {execution_time:.2f} seconds "
                f"(Metrics: {monitor_count}, Processes: {process_count}, Executions: {execution_count})"
            )
            
    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(f"Failed to cleanup old data after {execution_time:.2f} seconds: {e}")
        db.session.rollback()

def collect_advanced_metrics(app):
    """收集高级系统指标"""
    try:
        with app.app_context():
            # 收集IO统计
            io_stats = psutil.disk_io_counters()
            MonitorData(type='disk', metric='read_bytes', value=io_stats.read_bytes).save()
            MonitorData(type='disk', metric='write_bytes', value=io_stats.write_bytes).save()
            
            # 收集网络连接数
            connections = len(psutil.net_connections())
            MonitorData(type='network', metric='connections', value=connections).save()
            
            # 收集系统负载
            load_avg = psutil.getloadavg()
            MonitorData(type='system', metric='load_1', value=load_avg[0]).save()
            MonitorData(type='system', metric='load_5', value=load_avg[1]).save()
            MonitorData(type='system', metric='load_15', value=load_avg[2]).save()
            
            db.session.commit()
            
    except Exception as e:
        logger.error(f"Failed to collect advanced metrics: {e}")
        db.session.rollback()

def analyze_performance(app):
    """分析系统性能"""
    try:
        with app.app_context():
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=1)
            
            # 获取性能数据
            metrics = MonitorData.query.filter(
                MonitorData.timestamp.between(start_time, end_time)
            ).all()
            
            # 按类型分组数据
            data_by_type = {}
            for metric in metrics:
                if metric.type not in data_by_type:
                    data_by_type[metric.type] = []
                data_by_type[metric.type].append({
                    'timestamp': metric.timestamp,
                    'value': metric.value
                })
            
            # 分析结果
            analysis_results = {}
            
            # 分析每种类型的指标
            for metric_type, data in data_by_type.items():
                values = [d['value'] for d in data]
                if values:
                    analysis_results[metric_type] = {
                        'avg': sum(values) / len(values),
                        'max': max(values),
                        'min': min(values),
                        'current': values[-1] if values else 0,
                        'samples': len(values)
                    }
                    
                    # 计算趋势
                    if len(values) > 1:
                        trend = values[-1] - values[0]
                        analysis_results[metric_type]['trend'] = 'up' if trend > 0 else 'down'
                        analysis_results[metric_type]['trend_value'] = abs(trend)
            
            # 生成图表
            plt.figure(figsize=(12, 6))
            for metric_type, data in data_by_type.items():
                if data:
                    timestamps = [d['timestamp'] for d in data]
                    values = [d['value'] for d in data]
                    plt.plot(timestamps, values, label=metric_type)
            
            plt.title('System Performance Metrics')
            plt.xlabel('Time')
            plt.ylabel('Value')
            plt.legend()
            plt.grid(True)
            
            # 保存图表
            plot_path = f'static/performance_{datetime.now().strftime("%Y%m%d")}.png'
            plt.savefig(plot_path)
            plt.close()
            
            # 创建分析报告
            report = AnalysisReport(
                title='System Performance Analysis',
                report_type='performance',
                content={
                    'analysis': analysis_results,
                    'plot_path': plot_path,
                    'period': {
                        'start': start_time.isoformat(),
                        'end': end_time.isoformat()
                    }
                }
            )
            
            db.session.add(report)
            db.session.commit()
            
            # 检查性能问题
            if analysis_results.get('cpu', {}).get('avg', 0) > 70:
                log_system_event('WARNING', 'performance', 'High average CPU usage detected')
            if analysis_results.get('memory', {}).get('avg', 0) > 80:
                log_system_event('WARNING', 'performance', 'High average memory usage detected')
            
    except Exception as e:
        logger.error(f"Failed to analyze performance: {e}")
        db.session.rollback()

def predict_resource_usage(app):
    """预测资源使用趋势"""
    try:
        with app.app_context():
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=7)  # 使用过去7天的数据
            
            # 获取历史数据
            metrics = MonitorData.query.filter(
                MonitorData.timestamp.between(start_time, end_time)
            ).all()
            
            # 转换为DataFrame
            df = pd.DataFrame([{
                'timestamp': m.timestamp,
                'type': m.type,
                'metric': m.metric,
                'value': m.value
            } for m in metrics])
            
            # 按资源类型分组预测
            predictions = {}
            for resource_type in ['cpu', 'memory', 'disk']:
                resource_data = df[
                    (df['type'] == resource_type) & 
                    (df['metric'] == 'usage')
                ].sort_values('timestamp')
                
                if len(resource_data) > 0:
                    # 准备特征
                    X = np.array(range(len(resource_data))).reshape(-1, 1)
                    y = resource_data['value'].values
                    
                    # 训练模型
                    model = LinearRegression()
                    model.fit(X, y)
                    
                    # 预测未来24小时
                    future_X = np.array(range(len(resource_data), len(resource_data) + 24)).reshape(-1, 1)
                    future_y = model.predict(future_X)
                    
                    predictions[resource_type] = {
                        'current': y[-1],
                        'predicted': future_y.tolist(),
                        'trend': 'up' if model.coef_[0] > 0 else 'down',
                        'slope': float(model.coef_[0])
                    }
            
            # 生成预测报告
            report = AnalysisReport(
                title='Resource Usage Prediction',
                report_type='prediction',
                content={
                    'predictions': predictions,
                    'timestamp': datetime.utcnow().isoformat(),
                    'analysis_period': {
                        'start': start_time.isoformat(),
                        'end': end_time.isoformat()
                    }
                }
            )
            
            # 生成预测图表
            plt.figure(figsize=(12, 8))
            for resource_type, pred in predictions.items():
                plt.plot(pred['predicted'], label=f'{resource_type} (predicted)')
            plt.title('Resource Usage Prediction (Next 24 Hours)')
            plt.xlabel('Hours')
            plt.ylabel('Usage %')
            plt.legend()
            
            # 保存图表
            plot_path = f'static/predictions_{datetime.now().strftime("%Y%m%d")}.png'
            plt.savefig(plot_path)
            plt.close()
            
            # 更新报告内容
            report.content['plot_path'] = plot_path
            
            db.session.add(report)
            db.session.commit()
            
            # 检查是否需要发送告警
            for resource_type, pred in predictions.items():
                if pred['trend'] == 'up' and max(pred['predicted']) > 90:
                    logger.warning(
                        f"{resource_type} usage predicted to exceed 90% in the next 24 hours"
                    )
            
    except Exception as e:
        logger.error(f"Failed to predict resource usage: {e}")
        db.session.rollback() 