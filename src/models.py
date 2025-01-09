from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(db.Model, UserMixin):
    """用户模型"""
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(512), nullable=False)
    role = db.Column(db.String(20), default='user')
    active = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def is_active(self):
        return self.active

    def __repr__(self):
        return f'<User {self.username}>'

class MonitorData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50), nullable=False)  # cpu, memory, disk, network
    metric = db.Column(db.String(50), nullable=False)  # usage, bytes_sent, bytes_recv, etc.
    value = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<MonitorData {self.type}.{self.metric}: {self.value}>'

class ProcessData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pid = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    cpu_percent = db.Column(db.Float)
    memory_percent = db.Column(db.Float)
    status = db.Column(db.String(20))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<ProcessData {self.name}({self.pid})>'

class SystemLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    level = db.Column(db.String(20), nullable=False)  # INFO, WARNING, ERROR, etc.
    type = db.Column(db.String(50), nullable=False)  # system_metrics, backup, task, etc.
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<SystemLog {self.level} {self.type}: {self.message[:50]}...>'

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    cron_expression = db.Column(db.String(100))
    is_active = db.Column(db.Boolean, default=True)
    last_run = db.Column(db.DateTime)
    next_run = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Task {self.name}>'

class Asset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # 主机名
    ip_address = db.Column(db.String(45), nullable=False)  # IP地址
    type = db.Column(db.String(50), nullable=False)  # server, database, application, etc.
    os_type = db.Column(db.String(50))  # 操作系统类型
    os_version = db.Column(db.String(50))  # 操作系统版本
    cpu_cores = db.Column(db.Integer)  # CPU核心数
    memory_size = db.Column(db.Integer)  # 内存大小(GB)
    disk_size = db.Column(db.Integer)  # 磁盘大小(GB)
    description = db.Column(db.Text)  # 描述信息
    status = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Asset {self.name} ({self.ip_address})>'

class Backup(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # full, incremental
    status = db.Column(db.String(20), default='pending')  # pending, running, completed, failed
    source = db.Column(db.String(200), nullable=False)
    destination = db.Column(db.String(200), nullable=False)
    size = db.Column(db.BigInteger)  # in bytes
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Backup {self.name} ({self.type})>' 