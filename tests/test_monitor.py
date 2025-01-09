import unittest
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.monitor.system_monitor import SystemMonitor
from src.visualization.data_visualizer import DataVisualizer
from src.analysis.metrics_analyzer import MetricsAnalyzer
from src.export.data_exporter import DataExporter

class TestMonitoringSystem(unittest.TestCase):
    def setUp(self):
        self.config = {
            'thresholds': {
                'cpu_percent': 80,
                'memory_usage': 85,
                'disk_usage': 90
            },
            'db_path': 'test_monitor.db'
        }
        self.monitor = SystemMonitor(self.config)
        self.visualizer = DataVisualizer(self.config['db_path'])
        self.analyzer = MetricsAnalyzer(self.config['db_path'])
        self.exporter = DataExporter(self.config['db_path'])

    def test_collect_metrics(self):
        metrics = self.monitor.collect_system_metrics()
        self.assertIn('cpu_percent', metrics)
        self.assertIn('memory_usage', metrics)
        self.assertIn('disk_usage', metrics)
        self.assertIn('network', metrics)
        self.assertIn('database_status', metrics)

    def test_check_thresholds(self):
        self.monitor.collect_system_metrics()
        alerts = self.monitor.check_thresholds()
        self.assertIsInstance(alerts, dict)
        self.assertIn('cpu_percent_alert', alerts)

    def test_visualization(self):
        # 收集一些测试数据
        for _ in range(5):
            self.monitor.collect_system_metrics()
        
        # 测试创建仪表板
        try:
            self.visualizer.create_dashboard('test_dashboard.html')
            self.assertTrue(os.path.exists('test_dashboard.html'))
        finally:
            if os.path.exists('test_dashboard.html'):
                os.remove('test_dashboard.html')

    def test_analysis(self):
        # 收集一些测试数据
        for _ in range(5):
            self.monitor.collect_system_metrics()
        
        # 测试趋势分析
        analysis = self.analyzer.analyze_trends('cpu_percent')
        self.assertIn('current_value', analysis)
        self.assertIn('trend', analysis)

    def test_export(self):
        # 收集一些测试数据
        for _ in range(5):
            self.monitor.collect_system_metrics()
        
        # 测试导出功能
        try:
            self.exporter.export_to_csv('test_export.csv')
            self.assertTrue(os.path.exists('test_export.csv'))
        finally:
            if os.path.exists('test_export.csv'):
                os.remove('test_export.csv')

    def tearDown(self):
        # 清理测试数据库
        if os.path.exists(self.config['db_path']):
            os.remove(self.config['db_path'])

if __name__ == '__main__':
    unittest.main() 