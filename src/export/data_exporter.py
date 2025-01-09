import pandas as pd
import sqlite3
from typing import List, Optional
from datetime import datetime, timedelta

class DataExporter:
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    def export_to_csv(self, 
                      output_path: str,
                      metrics: Optional[List[str]] = None,
                      start_date: Optional[datetime] = None,
                      end_date: Optional[datetime] = None) -> None:
        """导出监控数据到CSV文件"""
        query = "SELECT * FROM metrics WHERE 1=1"
        params = []
        
        if metrics:
            query += " AND metric_name IN ({})".format(','.join(['?'] * len(metrics)))
            params.extend(metrics)
            
        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date)
            
        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date)
            
        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql_query(query, conn, params=params)
            df.to_csv(output_path, index=False)
    
    def export_to_json(self, output_path: str, **kwargs) -> None:
        """导出监控数据到JSON文件"""
        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql_query("SELECT * FROM metrics", conn)
            df.to_json(output_path, orient='records') 