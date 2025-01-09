from flask import Blueprint, render_template, jsonify, request, Response, stream_with_context, flash, redirect, url_for
from flask_login import login_required, current_user
from src.models import Task, SystemLog, MonitorData, Asset, Backup, ProcessData, db, MetricAlert, AnalysisReport, AutomationRule
from src.web.auth import permission_required
import psutil
from datetime import datetime, timedelta
from sqlalchemy import desc
import json
import re
import csv
import io
import subprocess
from typing import Dict, Optional
import logging
import nmap
from flask_wtf.csrf import generate_csrf
from src.utils.network_checker import NetworkChecker

main_bp = Blueprint('main', __name__)
api_bp = Blueprint('api', __name__, url_prefix='/api')

logger = logging.getLogger(__name__)

@main_bp.route('/')
@login_required
def index():
    # 获取系统信息
    cpu_percent = psutil.cpu_percent()
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    # 获取最近的任务
    recent_tasks = Task.query.order_by(desc(Task.created_at)).limit(5).all()
    
    # 获取最新日志
    recent_logs = SystemLog.query.order_by(desc(SystemLog.timestamp)).limit(5).all()
    
    return render_template('index.html',
                         cpu_percent=cpu_percent,
                         memory_percent=memory.percent,
                         disk_usage=disk.percent,
                         network_speed="计算中...",
                         recent_tasks=recent_tasks,
                         recent_logs=recent_logs)

@main_bp.route('/monitor')
@login_required
def monitor():
    # 获取24小时内的监控数据
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=24)
    
    monitor_data = MonitorData.query.filter(
        MonitorData.timestamp.between(start_time, end_time)
    ).order_by(MonitorData.timestamp.asc()).all()
    
    # 获取进程信息
    processes = ProcessData.query.order_by(desc(ProcessData.cpu_percent)).limit(10).all()
    
    return render_template('monitor.html',
                         monitor_data=monitor_data,
                         processes=processes)

@main_bp.route('/tasks')
@login_required
def tasks():
    tasks = Task.query.order_by(Task.created_at.desc()).all()
    return render_template('tasks.html', tasks=tasks)

@main_bp.route('/assets')
@login_required
def assets():
    """资产管理页面"""
    # 检查用户是否有查看资产的权限
    if not current_user.has_permission('view_assets'):
        flash('您没有权限访问资产管理页面', 'danger')
        return redirect(url_for('main.index'))
        
    assets = Asset.query.order_by(Asset.created_at.desc()).all()
    return render_template('assets.html', assets=assets)

@main_bp.route('/backups')
@login_required
def backups():
    backups = Backup.query.order_by(Backup.created_at.desc()).all()
    return render_template('backups.html', backups=backups)

@main_bp.route('/logs')
@login_required
def logs():
    """日志管理页面"""
    # 获取过滤参数
    level = request.args.get('level')
    type = request.args.get('type')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    search = request.args.get('search')
    page = request.args.get('page', 1, type=int)
    
    # 构建查询
    query = SystemLog.query
    
    if level:
        query = query.filter(SystemLog.level == level)
    if type:
        query = query.filter(SystemLog.type == type)
    if start_date:
        query = query.filter(SystemLog.timestamp >= datetime.strptime(start_date, '%Y-%m-%d'))
    if end_date:
        query = query.filter(SystemLog.timestamp <= datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1))
    if search:
        query = query.filter(SystemLog.message.contains(search))
    
    # 分页
    pagination = query.order_by(SystemLog.timestamp.desc()).paginate(
        page=page, per_page=50, error_out=False
    )
    
    # 获取日志类型和级别的统计信息
    level_stats = db.session.query(
        SystemLog.level, db.func.count(SystemLog.id)
    ).group_by(SystemLog.level).all()
    
    type_stats = db.session.query(
        SystemLog.type, db.func.count(SystemLog.id)
    ).group_by(SystemLog.type).all()
    
    return render_template('logs.html',
                         logs=pagination.items,
                         pagination=pagination,
                         level_stats=level_stats,
                         type_stats=type_stats,
                         current_level=level,
                         current_type=type,
                         start_date=start_date,
                         end_date=end_date,
                         search=search)

# API endpoints
@api_bp.route('/metrics/summary')
@login_required
def metrics_summary():
    try:
        cpu_percent = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return jsonify({
            'status': 'success',
            'data': {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'disk_usage': disk.percent,
                'timestamp': datetime.utcnow().isoformat()
            }
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500 

def validate_ip_address(ip_string):
    """验证 IP 地址格式"""
    pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    if not re.match(pattern, ip_string):
        return False
    
    # 验证每个数字是否在 0-255 范围内
    numbers = ip_string.split('.')
    for num in numbers:
        if not 0 <= int(num) <= 255:
            return False
    return True

@api_bp.route('/assets', methods=['POST'])
@login_required
@permission_required('manage_assets')
def create_asset():
    """创建新资产"""
    try:
        data = request.get_json()
        
        # 验证必需字段
        required_fields = ['name', 'ip_address', 'type']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'status': 'error',
                    'message': f'缺少必需字段: {field}'
                }), 400
        
        # 检查 IP 地址是否已存在
        if Asset.query.filter_by(ip_address=data['ip_address']).first():
            return jsonify({
                'status': 'error',
                'message': 'IP地址已存在'
            }), 400
        
        # 创建新资产
        new_asset = Asset(
            name=data['name'],
            ip_address=data['ip_address'],
            type=data['type'],
            status=data.get('status', 'unknown'),
            os_type=data.get('os_type'),
            os_version=data.get('os_version'),
            cpu_cores=data.get('cpu_cores'),
            memory_size=data.get('memory_size'),
            disk_size=data.get('disk_size'),
            description=data.get('description'),
            open_ports=data.get('open_ports', []),
            specs=data.get('specs', {}),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.session.add(new_asset)
        db.session.commit()
        
        # 记录操作日志
        log = SystemLog(
            level='info',
            type='asset',
            message=f'添加新资产: {new_asset.name} ({new_asset.ip_address})',
            user_id=current_user.id
        )
        db.session.add(log)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': '资产添加成功',
            'data': {
                'id': new_asset.id,
                'name': new_asset.name,
                'ip_address': new_asset.ip_address
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@api_bp.route('/assets/<int:asset_id>', methods=['PUT'])
@login_required
@permission_required('manage_assets')
def update_asset(asset_id):
    """更新资产信息"""
    try:
        asset = Asset.query.get_or_404(asset_id)
        data = request.get_json()
        
        # 更新资产信息
        for field in ['name', 'type', 'status', 'os_type', 'os_version', 
                     'cpu_cores', 'memory_size', 'disk_size', 'description']:
            if field in data:
                setattr(asset, field, data[field])
        
        # 特殊处理 IP 地址更新
        if 'ip_address' in data and data['ip_address'] != asset.ip_address:
            # 检查新 IP 是否已存在
            if Asset.query.filter_by(ip_address=data['ip_address']).first():
                return jsonify({
                    'status': 'error',
                    'message': '新IP地址已存在'
                }), 400
            asset.ip_address = data['ip_address']
        
        # 更新其他字段
        if 'open_ports' in data:
            asset.open_ports = data['open_ports']
        if 'specs' in data:
            asset.specs = data['specs']
        
        asset.updated_at = datetime.utcnow()
        db.session.commit()
        
        # 记录操作日志
        log = SystemLog(
            level='info',
            type='asset',
            message=f'更新资产: {asset.name} ({asset.ip_address})',
            user_id=current_user.id
        )
        db.session.add(log)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': '资产更新成功'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@api_bp.route('/assets/<int:asset_id>', methods=['DELETE'])
@login_required
@permission_required('manage_assets')
def delete_asset(asset_id):
    """删除资产"""
    try:
        asset = Asset.query.get_or_404(asset_id)
        
        # 记录操作日志
        log = SystemLog(
            level='warning',
            type='asset',
            message=f'删除资产: {asset.name} ({asset.ip_address})',
            user_id=current_user.id
        )
        
        db.session.delete(asset)
        db.session.add(log)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': '资产删除成功'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@api_bp.route('/assets/import', methods=['POST'])
@login_required
def import_assets():
    try:
        if 'file' not in request.files:
            return jsonify({
                'status': 'error',
                'message': '未上传文件'
            }), 400
            
        file = request.files['file']
        if not file.filename.endswith('.csv'):
            return jsonify({
                'status': 'error', 
                'message': '仅支持CSV文件'
            }), 400
            
        # 读取CSV文件
        stream = io.StringIO(file.stream.read().decode("UTF8"))
        csv_reader = csv.DictReader(stream)
        
        success_count = 0
        error_count = 0
        errors = []
        
        for row in csv_reader:
            try:
                # 验证必需字段
                if not all(key in row for key in ['name', 'ip_address', 'type']):
                    error_count += 1
                    errors.append(f'行 {csv_reader.line_num}: 缺少必需字段')
                    continue
                    
                # 验证IP地址
                if not validate_ip_address(row['ip_address']):
                    error_count += 1 
                    errors.append(f'行 {csv_reader.line_num}: IP地址格式不正确')
                    continue
                    
                # 检查IP是否已存在
                if Asset.query.filter_by(ip_address=row['ip_address']).first():
                    error_count += 1
                    errors.append(f'行 {csv_reader.line_num}: IP地址已存在')
                    continue
                
                # 创建资产
                asset = Asset()
                for key, value in row.items():
                    if hasattr(asset, key) and value:
                        if key in ['cpu_cores', 'memory_size', 'disk_size']:
                            value = int(value) if value else None
                        setattr(asset, key, value)
                
                db.session.add(asset)
                success_count += 1
                
            except Exception as e:
                error_count += 1
                errors.append(f'行 {csv_reader.line_num}: {str(e)}')
                continue
        
        if success_count > 0:
            db.session.commit()
            
        return jsonify({
            'status': 'success',
            'message': f'导入完成: 成功 {success_count} 条, 失败 {error_count} 条',
            'errors': errors
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500 

@api_bp.route('/assets/export', methods=['GET'])
@login_required
def export_assets():
    try:
        # 创建CSV内容
        output = io.StringIO()
        writer = csv.writer(output)
        
        # 写入表头
        headers = ['name', 'ip_address', 'type', 'os_type', 'os_version', 
                  'cpu_cores', 'memory_size', 'disk_size', 'description', 'status']
        writer.writerow(headers)
        
        # 写入数据
        assets = Asset.query.all()
        for asset in assets:
            writer.writerow([
                asset.name,
                asset.ip_address,
                asset.type,
                asset.os_type,
                asset.os_version,
                asset.cpu_cores,
                asset.memory_size,
                asset.disk_size,
                asset.description,
                asset.status
            ])
        
        # 设置响应头
        output.seek(0)
        return Response(
            output,
            mimetype='text/csv',
            headers={
                'Content-Disposition': 'attachment; filename=assets.csv'
            }
        )
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500 

def get_cpu_temperature() -> Optional[float]:
    """获取 CPU 温度"""
    methods = [
        # 方法1: 从 thermal_zone 读取
        lambda: open('/sys/class/thermal/thermal_zone0/temp', 'r').read().strip(),
        # 方法2: 从 coretemp 读取
        lambda: open('/sys/class/hwmon/hwmon0/temp1_input', 'r').read().strip(),
        # 方法3: 使用 sensors 命令
        lambda: subprocess.check_output(['sensors'], universal_newlines=True)
    ]
    
    for method in methods:
        try:
            result = method()
            if isinstance(result, str) and 'Core 0' in result:
                # sensors 命令输出
                for line in result.split('\n'):
                    if 'Core 0' in line:
                        return float(line.split('+')[1].split('°')[0])
            else:
                # thermal_zone 或 hwmon 读取
                return float(result) / 1000.0
        except Exception as e:
            logger.debug(f"Temperature reading method failed: {str(e)}")
            continue
            
    logger.warning("Failed to read CPU temperature from all methods")
    return None

def get_disk_temperature() -> Dict[str, float]:
    """获取硬盘温度"""
    temperatures = {}
    
    try:
        # 获取所有磁盘设备
        disks = []
        output = subprocess.check_output(['lsblk', '-d', '-o', 'NAME'], universal_newlines=True)
        for line in output.split('\n')[1:]:  # 跳过标题行
            if line.strip():
                disks.append(line.strip())
        
        # 获取每个磁盘的温度
        for disk in disks:
            try:
                output = subprocess.check_output(
                    ['sudo', 'smartctl', '-A', f'/dev/{disk}'],
                    universal_newlines=True
                )
                for line in output.split('\n'):
                    if any(temp in line.lower() for temp in ['temperature_celsius', 'airflow_temp']):
                        temp = float(line.split()[9])
                        temperatures[f'/dev/{disk}'] = temp
                        break
            except Exception as e:
                logger.debug(f"Failed to read temperature for disk {disk}: {str(e)}")
                
    except Exception as e:
        logger.warning(f"Failed to list block devices: {str(e)}")
        
    if not temperatures:
        logger.warning("No disk temperatures could be read")
        
    return temperatures

@api_bp.route('/metrics/realtime')
@login_required
def get_realtime_metrics():
    """获取实时系统指标"""
    try:
        # CPU 信息
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        cpu_freq = psutil.cpu_freq()
        
        # 内存信息
        memory = psutil.virtual_memory()
        
        # 磁盘信息
        disk = psutil.disk_usage('/')
        
        # 网络信息
        net_io = psutil.net_io_counters()
        
        # 系统负载
        load_avg = psutil.getloadavg()
        
        # 获取TOP进程
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'status']):
            try:
                pinfo = proc.info
                processes.append({
                    'pid': pinfo['pid'],
                    'name': pinfo['name'],
                    'cpu_percent': pinfo['cpu_percent'] or 0,
                    'memory_percent': pinfo['memory_percent'] or 0,
                    'status': pinfo['status']
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        # 按 CPU 使用率排序,取前10个
        processes.sort(key=lambda x: x['cpu_percent'], reverse=True)
        processes = processes[:10]
        
        # 获取温度信息
        cpu_temp = get_cpu_temperature()
        disk_temps = get_disk_temperature()
        
        return jsonify({
            'status': 'success',
            'data': {
                'cpu': {
                    'usage': cpu_percent,
                    'count': cpu_count,
                    'freq_current': cpu_freq.current if cpu_freq else 0,
                    'freq_min': cpu_freq.min if cpu_freq else 0,
                    'freq_max': cpu_freq.max if cpu_freq else 0,
                    'load_avg': load_avg
                },
                'memory': {
                    'total': memory.total,
                    'available': memory.available,
                    'used': memory.used,
                    'percent': memory.percent
                },
                'disk': {
                    'total': disk.total,
                    'used': disk.used,
                    'free': disk.free,
                    'percent': disk.percent
                },
                'network': {
                    'bytes_sent': net_io.bytes_sent,
                    'bytes_recv': net_io.bytes_recv,
                    'packets_sent': net_io.packets_sent,
                    'packets_recv': net_io.packets_recv,
                    'errin': net_io.errin,
                    'errout': net_io.errout
                },
                'processes': processes,
                'temperature': {
                    'cpu': cpu_temp,
                    'disks': disk_temps
                },
                'timestamp': datetime.now().isoformat()
            }
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500 

@api_bp.route('/logs/export', methods=['GET'])
@login_required
def export_logs():
    """导出日志"""
    try:
        # 获取过滤参数
        level = request.args.get('level')
        type = request.args.get('type')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        search = request.args.get('search')
        
        # 构建查询
        query = SystemLog.query
        
        if level:
            query = query.filter(SystemLog.level == level)
        if type:
            query = query.filter(SystemLog.type == type)
        if start_date:
            query = query.filter(SystemLog.timestamp >= datetime.strptime(start_date, '%Y-%m-%d'))
        if end_date:
            query = query.filter(SystemLog.timestamp <= datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1))
        if search:
            query = query.filter(SystemLog.message.contains(search))
            
        # 获取日志数据
        logs = query.order_by(SystemLog.timestamp.desc()).all()
        
        # 创建CSV内容
        output = io.StringIO()
        writer = csv.writer(output)
        
        # 写入表头
        writer.writerow(['时间', '级别', '类型', '消息'])
        
        # 写入数据
        for log in logs:
            writer.writerow([
                log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                log.level,
                log.type,
                log.message
            ])
            
        # 设置响应头
        output.seek(0)
        return Response(
            output,
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename=logs_{datetime.now().strftime("%Y%m%d")}.csv'
            }
        )
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

def log_system_event(level: str, event_type: str, message: str, user_id: Optional[int] = None):
    """记录系统事件"""
    try:
        log = SystemLog(
            level=level,
            type=event_type,
            message=message,
            user_id=user_id
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        logger.error(f"Failed to log system event: {e}")
        db.session.rollback()

@api_bp.route('/alerts', methods=['GET', 'POST'])
@login_required
def manage_alerts():
    if request.method == 'POST':
        data = request.get_json()
        alert = MetricAlert(
            name=data['name'],
            metric_type=data['metric_type'],
            metric_name=data['metric_name'],
            condition=data['condition'],
            threshold=float(data['threshold']),
            duration=int(data['duration']),
            severity=data['severity'],
            notify_channels=data['notify_channels']
        )
        db.session.add(alert)
        db.session.commit()
        return jsonify({'status': 'success'})
    
    alerts = MetricAlert.query.all()
    return jsonify([{
        'id': alert.id,
        'name': alert.name,
        'metric_type': alert.metric_type,
        'threshold': alert.threshold,
        'enabled': alert.enabled
    } for alert in alerts])

@api_bp.route('/reports')
@login_required
def get_reports():
    report_type = request.args.get('type', 'performance')
    reports = AnalysisReport.query.filter_by(
        report_type=report_type
    ).order_by(AnalysisReport.created_at.desc()).all()
    
    return jsonify([{
        'id': report.id,
        'title': report.title,
        'content': report.content,
        'created_at': report.created_at.isoformat()
    } for report in reports])

@api_bp.route('/automation/rules', methods=['GET', 'POST'])
@login_required
def manage_automation_rules():
    if request.method == 'POST':
        data = request.get_json()
        rule = AutomationRule(
            name=data['name'],
            trigger_type=data['trigger_type'],
            trigger_condition=data['trigger_condition'],
            actions=data['actions']
        )
        db.session.add(rule)
        db.session.commit()
        return jsonify({'status': 'success'})
    
    rules = AutomationRule.query.all()
    return jsonify([{
        'id': rule.id,
        'name': rule.name,
        'trigger_type': rule.trigger_type,
        'enabled': rule.enabled
    } for rule in rules]) 

@main_bp.route('/analysis')
@login_required
def analysis():
    """系统分析页面"""
    # 获取最新的性能报告
    performance_report = AnalysisReport.query.filter_by(
        report_type='performance'
    ).order_by(AnalysisReport.created_at.desc()).first()
    
    # 获取最新的预测报告
    prediction_report = AnalysisReport.query.filter_by(
        report_type='prediction'
    ).order_by(AnalysisReport.created_at.desc()).first()
    
    return render_template('analysis.html',
                         performance_report=performance_report,
                         prediction_report=prediction_report)

@api_bp.route('/analysis/performance')
@login_required
def get_performance_analysis():
    """获取性能分析数据"""
    days = request.args.get('days', 7, type=int)
    reports = AnalysisReport.query.filter_by(
        report_type='performance'
    ).order_by(
        AnalysisReport.created_at.desc()
    ).limit(days).all()
    
    return jsonify([{
        'id': report.id,
        'title': report.title,
        'content': report.content,
        'created_at': report.created_at.isoformat()
    } for report in reports])

@api_bp.route('/analysis/prediction')
@login_required
def get_resource_prediction():
    """获取资源使用预测"""
    report = AnalysisReport.query.filter_by(
        report_type='prediction'
    ).order_by(
        AnalysisReport.created_at.desc()
    ).first()
    
    if not report:
        return jsonify({
            'status': 'error',
            'message': 'No prediction data available'
        }), 404
        
    return jsonify({
        'status': 'success',
        'data': report.content
    }) 

@main_bp.route('/alerts')
@login_required
def alerts():
    """告警管理页面"""
    alerts = MetricAlert.query.all()
    return render_template('alerts.html', alerts=alerts)

@api_bp.route('/alerts/<int:alert_id>/toggle', methods=['POST'])
@login_required
def toggle_alert(alert_id):
    """切换告警规则状态"""
    try:
        alert = MetricAlert.query.get_or_404(alert_id)
        alert.enabled = not alert.enabled
        db.session.commit()
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500 

@main_bp.route('/automation')
@login_required
def automation():
    """自动化规则管理页面"""
    rules = AutomationRule.query.all()
    return render_template('automation.html', rules=rules)

@api_bp.route('/automation/rules/<int:rule_id>/toggle', methods=['POST'])
@login_required
def toggle_rule(rule_id):
    """切换自动化规则状态"""
    try:
        rule = AutomationRule.query.get_or_404(rule_id)
        rule.enabled = not rule.enabled
        db.session.commit()
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500 

@api_bp.route('/assets/scan')
@login_required
def scan_assets():
    """扫描网络资产"""
    try:
        networks = request.args.get('networks', '').split(',')
        options = json.loads(request.args.get('options', '{}'))
        
        if not networks:
            return jsonify({
                'status': 'error',
                'message': '请指定要扫描的网段'
            }), 400
            
        def generate():
            try:
                # 初始化扫描器
                nm = nmap.PortScanner()
                yield json_line({
                    'status': 'info',
                    'message': '初始化扫描器成功',
                    'progress': 0
                })

                for network in networks:
                    try:
                        # 使用简单的 ping 扫描发现主机
                        yield json_line({
                            'status': 'info',
                            'message': f'正在扫描网段 {network} 中的活跃主机...',
                            'progress': 10
                        })

                        # 使用 -sn 选项进行主机发现（不需要root权限）
                        ping_result = nm.scan(hosts=network, arguments='-sn')
                        
                        # 获取活跃主机列表
                        active_hosts = [host for host in nm.all_hosts()]
                        
                        if not active_hosts:
                            yield json_line({
                                'status': 'warning',
                                'message': f'在网段 {network} 中未发现活跃主机',
                                'progress': 20
                            })
                            continue

                        yield json_line({
                            'status': 'success',
                            'message': f'发现 {len(active_hosts)} 个活跃主机',
                            'progress': 30
                        })

                        # 对每个活跃主机进行详细扫描
                        total_hosts = len(active_hosts)
                        for index, host in enumerate(active_hosts, 1):
                            try:
                                yield json_line({
                                    'status': 'info',
                                    'message': f'正在扫描主机 {host} ({index}/{total_hosts})...',
                                    'progress': 30 + int((index / total_hosts) * 60)
                                })

                                # 使用不需要root权限的扫描选项
                                scan_args = '-sT -Pn -F --version-light'  # -sT: TCP连接扫描, -F: 快速扫描
                                host_result = nm.scan(hosts=host, arguments=scan_args)

                                if host in nm.all_hosts():
                                    host_data = nm[host]
                                    
                                    # 构建资产数据
                                    asset_data = {
                                        'ip': host,
                                        'hostname': host_data.get('hostname', ''),
                                        'os_type': 'Unknown',
                                        'os_version': 'Unknown',
                                        'open_ports': []
                                    }

                                    # 获取端口信息
                                    if 'tcp' in host_data:
                                        for port, info in host_data['tcp'].items():
                                            if info['state'] == 'open':
                                                port_info = {
                                                    'port': port,
                                                    'service': info.get('name', 'unknown'),
                                                    'version': info.get('version', '')
                                                }
                                                asset_data['open_ports'].append(port_info)

                                    yield json_line({
                                        'status': 'success',
                                        'message': f'发现主机: {host}',
                                        'progress': 30 + int((index / total_hosts) * 60),
                                        'found_asset': asset_data
                                    })

                            except Exception as e:
                                logger.error(f"扫描主机 {host} 时出错: {e}")
                                yield json_line({
                                    'status': 'error',
                                    'message': f'扫描主机 {host} 时出错: {str(e)}',
                                    'progress': 30 + int((index / total_hosts) * 60)
                                })

                    except Exception as e:
                        logger.error(f"扫描网段 {network} 时出错: {e}")
                        yield json_line({
                            'status': 'error',
                            'message': f'扫描网段 {network} 时出错: {str(e)}',
                            'progress': 50
                        })

                yield json_line({
                    'status': 'success',
                    'message': '扫描完成',
                    'progress': 100
                })

            except Exception as e:
                logger.error(f"扫描过程出错: {e}")
                yield json_line({
                    'status': 'error',
                    'message': f'扫描过程出错: {str(e)}',
                    'progress': 100
                })

        return Response(
            stream_with_context(generate()),
            mimetype='text/event-stream'
        )

    except Exception as e:
        logger.error(f"扫描请求处理出错: {e}")
        return jsonify({
            'status': 'error',
            'message': f'扫描请求处理出错: {str(e)}'
        }), 500

def json_line(data):
    """生成 JSON 行"""
    return json.dumps(data, ensure_ascii=False) + '\n'

@api_bp.route('/assets/scan/cancel', methods=['POST'])
@login_required
def cancel_scan():
    """取消资产扫描"""
    # 实现取消扫描的逻辑
    return jsonify({'status': 'success'}) 

@main_bp.context_processor
def inject_csrf_token():
    """确保所有模板都能访问 csrf_token"""
    return dict(csrf_token=generate_csrf) 

@api_bp.route('/assets/check/<int:asset_id>', methods=['POST'])
@login_required
def check_asset(asset_id):
    """检测资产状态"""
    try:
        asset = Asset.query.get_or_404(asset_id)
        checker = NetworkChecker()
        
        # 执行全面扫描
        results = checker.scan_all_services(asset.ip_address)
        
        # 更新资产状态
        if results['ping']['status'] == 'online':
            asset.status = 'online'
            asset.response_time = results['ping']['response_time']
            
            # 更新端口信息
            if results['ports']['status'] == 'success':
                asset.open_ports = results['ports']['open_ports']
            
            # 更新服务信息
            asset.services = results['services']
            
        else:
            asset.status = 'offline'
        
        asset.last_check = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'data': results
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500 