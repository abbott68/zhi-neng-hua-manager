from monitor.system_monitor import SystemMonitor
from alert.alert_manager import AlertManager
import time
import yaml
from visualization.data_visualizer import DataVisualizer
from analysis.metrics_analyzer import MetricsAnalyzer
from export.data_exporter import DataExporter
from datetime import datetime, timedelta

def load_config(config_path: str) -> dict:
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def main():
    # 加载配置
    config = load_config('config.yml')
    
    # 初始化监控和告警系统
    monitor = SystemMonitor()
    alert_manager = AlertManager(config['smtp'])
    
    # 初始化新组件
    visualizer = DataVisualizer(config['db_path'])
    analyzer = MetricsAnalyzer(config['db_path'])
    exporter = DataExporter(config['db_path'])
    
    while True:
        # 收集指标
        metrics = monitor.collect_system_metrics()
        
        # 检查阈值
        alerts = monitor.check_thresholds()
        
        # 处理告警
        for alert_type, is_alert in alerts.items():
            if is_alert:
                # 获取趋势分析
                analysis = analyzer.analyze_trends(alert_type.replace('_alert', ''))
                predictions = analyzer.predict_next_hours(alert_type.replace('_alert', ''))
                
                alert_message = (
                    f"系统指标超过阈值: {metrics}\n"
                    f"趋势分析: {analysis}\n"
                    f"未来6小时预测: {predictions}"
                )
                
                alert_manager.send_alert(alert_type, alert_message, config['alert_recipients'])
        
        # 每天更新一次仪表板
        if datetime.now().hour == 0:
            visualizer.create_dashboard()
            
            # 导出昨天的数据
            yesterday = datetime.now() - timedelta(days=1)
            exporter.export_to_csv(
                f"metrics_{yesterday.strftime('%Y%m%d')}.csv",
                start_date=yesterday,
                end_date=datetime.now()
            )
        
        time.sleep(config['check_interval'])

if __name__ == '__main__':
    main() 