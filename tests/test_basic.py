import unittest
import os
from src.monitor.system_monitor import SystemMonitor

class TestBasicMonitoring(unittest.TestCase):
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

    def test_basic_metrics(self):
        metrics = self.monitor.collect_system_metrics()
        self.assertIn('cpu_percent', metrics)
        self.assertIn('memory_usage', metrics)
        self.assertIn('disk_usage', metrics)

    def tearDown(self):
        if os.path.exists(self.config['db_path']):
            os.remove(self.config['db_path'])

if __name__ == '__main__':
    unittest.main() 