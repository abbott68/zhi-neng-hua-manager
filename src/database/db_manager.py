from typing import Dict, Any, Optional
import sqlite3
from datetime import datetime

class DatabaseManager:
    def __init__(self, config: Dict[str, Any]):
        self.sqlite_path = config.get('db_path', 'monitor.db')
        self.mongo_enabled = False
        self.mysql_enabled = False
        
        # 尝试导入可选的数据库模块
        try:
            import pymongo
            self.mongo_enabled = True
            self.mongo_config = config.get('mongodb', {})
            self.mongo_client = None
        except ImportError:
            print("MongoDB support not available")
            
        try:
            import mysql.connector
            self.mysql_enabled = True
            self.mysql_config = config.get('mysql', {})
        except ImportError:
            print("MySQL support not available")
            
        self.init_databases()
        
    def init_databases(self) -> None:
        """初始化所有数据库连接"""
        self._init_sqlite()
    
    def _init_sqlite(self) -> None:
        """初始化SQLite数据库"""
        try:
            with sqlite3.connect(self.sqlite_path) as conn:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME,
                        metric_name TEXT,
                        metric_value REAL
                    )
                ''')
                # 添加索引以提高查询性能
                conn.execute('''
                    CREATE INDEX IF NOT EXISTS idx_metrics_timestamp 
                    ON metrics(timestamp)
                ''')
                conn.execute('''
                    CREATE INDEX IF NOT EXISTS idx_metrics_name 
                    ON metrics(metric_name)
                ''')
                print(f"SQLite database initialized at {self.sqlite_path}")
        except Exception as e:
            print(f"Error initializing SQLite database: {e}")
    
    def save_metrics(self, metrics: Dict[str, Any]) -> None:
        """保存指标到所有可用的数据库"""
        self._save_to_sqlite(metrics)
        if self.mongo_enabled:
            self._save_to_mongo(metrics)
        if self.mysql_enabled:
            self._save_to_mysql(metrics)
    
    def _save_to_sqlite(self, metrics: Dict[str, Any]) -> None:
        """保存到SQLite"""
        current_time = datetime.now()
        with sqlite3.connect(self.sqlite_path) as conn:
            for metric_name, metric_value in metrics.items():
                if isinstance(metric_value, (int, float)):
                    conn.execute(
                        'INSERT INTO metrics (timestamp, metric_name, metric_value) VALUES (?, ?, ?)',
                        (current_time, metric_name, metric_value)
                    )
    
    def _save_to_mongo(self, metrics: Dict[str, Any]) -> None:
        """保存到MongoDB"""
        if not self.mongo_enabled:
            return
            
        try:
            import pymongo
            client = pymongo.MongoClient(**self.mongo_config)
            db = client.monitoring
            db.metrics.insert_one({
                'timestamp': datetime.now(),
                'metrics': metrics
            })
        except Exception as e:
            print(f"MongoDB保存失败: {e}")
    
    def _save_to_mysql(self, metrics: Dict[str, Any]) -> None:
        """保存到MySQL"""
        if not self.mysql_enabled:
            return
            
        try:
            import mysql.connector
            conn = mysql.connector.connect(**self.mysql_config)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS metrics (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    timestamp DATETIME,
                    metric_name VARCHAR(255),
                    metric_value FLOAT
                )
            ''')
            
            current_time = datetime.now()
            for metric_name, metric_value in metrics.items():
                if isinstance(metric_value, (int, float)):
                    cursor.execute(
                        'INSERT INTO metrics (timestamp, metric_name, metric_value) VALUES (%s, %s, %s)',
                        (current_time, metric_name, metric_value)
                    )
            
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"MySQL保存失败: {e}")
    
    def check_connections(self) -> Dict[str, bool]:
        """检查所有可用数据库连接"""
        status = {
            'sqlite': self._check_sqlite()
        }
        
        if self.mongo_enabled:
            status['mongodb'] = self._check_mongo()
        if self.mysql_enabled:
            status['mysql'] = self._check_mysql()
            
        return status
    
    def _check_sqlite(self) -> bool:
        try:
            with sqlite3.connect(self.sqlite_path) as conn:
                conn.execute("SELECT 1")
            return True
        except Exception:
            return False
    
    def _check_mongo(self) -> bool:
        if not self.mongo_enabled:
            return False
        try:
            import pymongo
            client = pymongo.MongoClient(**self.mongo_config)
            client.server_info()
            return True
        except Exception:
            return False
    
    def _check_mysql(self) -> bool:
        if not self.mysql_enabled:
            return False
        try:
            import mysql.connector
            conn = mysql.connector.connect(**self.mysql_config)
            status = conn.is_connected()
            conn.close()
            return status
        except Exception:
            return False 