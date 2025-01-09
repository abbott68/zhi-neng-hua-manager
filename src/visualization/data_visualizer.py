import pandas as pd
import sqlite3
from typing import List
from datetime import datetime, timedelta

class DataVisualizer:
    def __init__(self, db_path: str):
        self.db_path = db_path
        
    def get_metrics_data(self, metrics: List[str], days: int = 7) -> pd.DataFrame:
        """从数据库获取指定指标的历史数据"""
        query = """
            SELECT timestamp, metric_name, metric_value 
            FROM metrics 
            WHERE metric_name IN ({})
            AND timestamp >= datetime('now', '-{} days')
        """.format(','.join(['?'] * len(metrics)), days)
        
        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql_query(query, conn, params=metrics)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            return df 