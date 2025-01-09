from typing import Dict, Any, List
import psutil
import time
from datetime import datetime, timedelta
from src.models import MonitorData, ProcessData, SystemLog, db
import logging

logger = logging.getLogger(__name__)

class SystemMonitor:
    def __init__(self, config: Dict):
        self.metrics: Dict[str, Any] = {}
        self.config = config  # 保存配置
        self.thresholds = config.get('thresholds', {
            'cpu_percent': 80,
            'memory_usage': 85,
            'disk_usage': 90,
            'bytes_sent': 1000000000,  # 1GB
            'bytes_recv': 1000000000   # 1GB
        })
        self._last_network = self._get_network_metrics()
        self._last_network_time = time.time()
        logger.info("System monitor initialized")
    
    def collect_system_metrics(self) -> Dict[str, Any]:
        """收集系统指标"""
        try:
            # 收集基本指标
            cpu_percent = psutil.cpu_percent(interval=0.1)  # 使用较短的间隔
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # 收集网络指标
            try:
                network = self._get_network_metrics()
            except Exception as e:
                logger.error(f"Failed to collect network metrics: {e}")
                network = {}
            
            # 收集进程信息
            try:
                processes = self._get_top_processes()
            except Exception as e:
                logger.error(f"Failed to collect process info: {e}")
                processes = []
            
            # 更新内存中的指标
            self.metrics = {
                'cpu_percent': cpu_percent or 0.0,
                'memory_usage': memory.percent,
                'disk_usage': disk.percent,
                'timestamp': datetime.now().isoformat(),
                'network': network,
                'processes': processes,
                'system_info': self._get_system_info()
            }
            
            # 记录调试信息
            logger.debug(f"Collected metrics: {self.metrics}")
            
            # 保存到数据库
            try:
                current_time = datetime.utcnow()
                metrics_data = [
                    MonitorData(
                        type='cpu',
                        metric='usage',
                        value=cpu_percent or 0.0,
                        timestamp=current_time
                    ),
                    MonitorData(
                        type='memory',
                        metric='usage',
                        value=memory.percent,
                        timestamp=current_time
                    ),
                    MonitorData(
                        type='disk',
                        metric='usage',
                        value=disk.percent,
                        timestamp=current_time
                    )
                ]
                
                # 添加网络指标
                if network:
                    metrics_data.extend([
                        MonitorData(
                            type='network',
                            metric='bytes_sent_speed',
                            value=network.get('bytes_sent_speed', 0),
                            timestamp=current_time
                        ),
                        MonitorData(
                            type='network',
                            metric='bytes_recv_speed',
                            value=network.get('bytes_recv_speed', 0),
                            timestamp=current_time
                        )
                    ])
                
                db.session.bulk_save_objects(metrics_data)
                db.session.commit()
                
                # 清理旧数据
                retention_days = self.config.get('retention_days', 30)
                cleanup_before = current_time - timedelta(days=retention_days)
                db.session.query(MonitorData).filter(
                    MonitorData.timestamp < cleanup_before
                ).delete()
                db.session.commit()
                
            except Exception as e:
                logger.error(f"Failed to save metrics to database: {e}")
                db.session.rollback()
            
            return self.metrics
            
        except Exception as e:
            logger.error(f"Error collecting metrics: {e}", exc_info=True)
            return {
                'cpu_percent': 0.0,
                'memory_usage': 0.0,
                'disk_usage': 0.0,
                'timestamp': datetime.now().isoformat(),
                'network': {},
                'processes': [],
                'system_info': {}
            }
    
    def _get_network_metrics(self) -> Dict[str, Any]:
        """获取网络指标"""
        try:
            current_time = time.time()
            net_io = psutil.net_io_counters()
            current_stats = {
                'bytes_sent': net_io.bytes_sent,
                'bytes_recv': net_io.bytes_recv,
                'packets_sent': net_io.packets_sent,
                'packets_recv': net_io.packets_recv,
                'errin': net_io.errin,
                'errout': net_io.errout,
                'dropin': net_io.dropin,
                'dropout': net_io.dropout
            }

            # 计算网络速率
            if hasattr(self, '_last_network'):
                time_diff = max(current_time - self._last_network_time, 0.1)  # 避免除以零
                current_stats.update({
                    'bytes_sent_speed': (current_stats['bytes_sent'] - self._last_network['bytes_sent']) / time_diff,
                    'bytes_recv_speed': (current_stats['bytes_recv'] - self._last_network['bytes_recv']) / time_diff,
                    'packets_sent_speed': (current_stats['packets_sent'] - self._last_network['packets_sent']) / time_diff,
                    'packets_recv_speed': (current_stats['packets_recv'] - self._last_network['packets_recv']) / time_diff
                })
            else:
                current_stats.update({
                    'bytes_sent_speed': 0,
                    'bytes_recv_speed': 0,
                    'packets_sent_speed': 0,
                    'packets_recv_speed': 0
                })

            # 更新上次的网络数据
            self._last_network = current_stats
            self._last_network_time = current_time

            return current_stats
        except Exception as e:
            logger.error(f"Error getting network metrics: {e}")
            return {
                'bytes_sent': 0,
                'bytes_recv': 0,
                'packets_sent': 0,
                'packets_recv': 0,
                'errin': 0,
                'errout': 0,
                'dropin': 0,
                'dropout': 0,
                'bytes_sent_speed': 0,
                'bytes_recv_speed': 0,
                'packets_sent_speed': 0,
                'packets_recv_speed': 0
            }
    
    def _get_top_processes(self, limit: int = 5) -> List[Dict[str, Any]]:
        """获取资源占用最高的进程"""
        processes = []
        try:
            # 先收集一次 CPU 使用率
            for proc in psutil.process_iter(['pid', 'name', 'status']):
                try:
                    proc.cpu_percent()
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
            
            # 等待一小段时间
            time.sleep(0.1)
            
            # 再次收集进程信息
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'status']):
                try:
                    pinfo = proc.info
                    cpu_percent = pinfo.get('cpu_percent', 0.0)
                    memory_percent = pinfo.get('memory_percent', 0.0)
                    
                    if cpu_percent is None:
                        cpu_percent = 0.0
                    if memory_percent is None:
                        memory_percent = 0.0
                    
                    processes.append({
                        'pid': pinfo['pid'],
                        'name': pinfo['name'],
                        'cpu_percent': cpu_percent,
                        'memory_percent': memory_percent,
                        'status': pinfo['status']
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
                except Exception as e:
                    logger.error(f"Error getting process info: {e}")
                    continue
            
            # 按 CPU 使用率排序，确保所有值都是数字
            processes.sort(key=lambda x: float(x['cpu_percent'] or 0), reverse=True)
            return processes[:limit]
            
        except Exception as e:
            logger.error(f"Error in _get_top_processes: {e}", exc_info=True)
            return []
    
    def _get_system_info(self) -> Dict[str, Any]:
        """获取系统信息"""
        try:
            cpu_freq = psutil.cpu_freq()
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                'cpu_count': psutil.cpu_count(),
                'cpu_count_logical': psutil.cpu_count(logical=True),
                'cpu_freq_current': cpu_freq.current if cpu_freq else 0,
                'cpu_freq_min': cpu_freq.min if cpu_freq else 0,
                'cpu_freq_max': cpu_freq.max if cpu_freq else 0,
                'memory_total': memory.total,
                'memory_available': memory.available,
                'disk_total': disk.total,
                'disk_used': disk.used,
                'disk_free': disk.free,
                'boot_time': datetime.fromtimestamp(psutil.boot_time()).isoformat()
            }
        except Exception as e:
            logger.error(f"Error collecting system info: {e}")
            return {}
    
    def _log_metrics(self):
        """记录指标到日志"""
        # 检查是否超过阈值
        alerts = self.check_thresholds()
        if any(alerts.values()):
            log = SystemLog(
                level='WARNING',
                type='system_metrics',
                message=f"Thresholds exceeded: {[k for k, v in alerts.items() if v]}"
            )
            db.session.add(log)
            db.session.commit()
    
    def check_thresholds(self) -> Dict[str, bool]:
        """检查是否超过阈值"""
        alerts = {}
        for metric, threshold in self.thresholds.items():
            if metric in self.metrics:
                if isinstance(self.metrics[metric], (int, float)):
                    alerts[f'{metric}_alert'] = self.metrics[metric] > threshold
            elif metric in self.metrics.get('network', {}):
                value = self.metrics['network'][metric]
                alerts[f'{metric}_alert'] = value > threshold
        return alerts 