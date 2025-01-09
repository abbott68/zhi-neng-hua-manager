import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from typing import Dict
import sqlite3
from datetime import datetime, timedelta

class MetricsAnalyzer:
    def __init__(self, db_path: str):
        self.db_path = db_path
        
    def analyze_trends(self, metric_name: str, hours: int = 24) -> Dict:
        """分析指标趋势"""
        query = """
            SELECT timestamp, metric_value 
            FROM metrics 
            WHERE metric_name = ? 
            AND timestamp >= datetime('now', '-{} hours')
            ORDER BY timestamp
        """.format(hours)
        
        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql_query(query, conn, params=(metric_name,))
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        if len(df) == 0:
            return {
                'current_value': 0,
                'mean': 0,
                'max': 0,
                'min': 0,
                'std': 0,
                'trend': 'no data'
            }
            
        return {
            'current_value': df['metric_value'].iloc[-1],
            'mean': df['metric_value'].mean(),
            'max': df['metric_value'].max(),
            'min': df['metric_value'].min(),
            'std': df['metric_value'].std(),
            'trend': self._calculate_trend(df['metric_value'])
        }
    
    def predict_next_hours(self, metric_name: str, hours: int = 6) -> Dict[str, float]:
        """预测未来几小时的指标值"""
        query = """
            SELECT timestamp, metric_value 
            FROM metrics 
            WHERE metric_name = ? 
            ORDER BY timestamp DESC 
            LIMIT 168
        """
        
        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql_query(query, conn, params=(metric_name,))
            
        if len(df) < 2:
            return {}
            
        df['hour'] = pd.to_datetime(df['timestamp']).dt.hour
        df['day_of_week'] = pd.to_datetime(df['timestamp']).dt.dayofweek
        
        X = df[['hour', 'day_of_week']]
        y = df['metric_value']
        
        model = LinearRegression()
        model.fit(X, y)
        
        current_time = datetime.now()
        future_times = pd.date_range(current_time, periods=hours, freq='H')
        
        future_features = pd.DataFrame({
            'hour': future_times.hour,
            'day_of_week': future_times.dayofweek
        })
        
        predictions = model.predict(future_features)
        
        return {str(time): pred for time, pred in zip(future_times, predictions)}
    
    def _calculate_trend(self, values: pd.Series) -> str:
        """计算趋势方向"""
        if len(values) < 2:
            return "stable"
            
        slope = np.polyfit(range(len(values)), values, 1)[0]
        
        if slope > 0.1:
            return "increasing"
        elif slope < -0.1:
            return "decreasing"
        else:
            return "stable" 