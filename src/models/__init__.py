from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from enum import Enum
from werkzeug.security import generate_password_hash

db = SQLAlchemy()

class UserRole(Enum):
    ADMIN = 'admin'          # 管理员
    OPERATOR = 'operator'    # 运维人员
    VIEWER = 'viewer'        # 只读用户

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    email = db.Column(db.String(120), unique=True)
    role = db.Column(db.String(20), default=UserRole.VIEWER.value)
    department = db.Column(db.String(50))  # 部门
    active = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def has_permission(self, permission):
        """检查用户是否有特定权限"""
        role_permissions = {
            UserRole.ADMIN.value: [
                'manage_users',
                'manage_assets',
                'manage_tasks',
                'view_assets',
                'view_logs',
                'manage_backups',
                'manage_alerts',
                'manage_automation'
            ],
            UserRole.OPERATOR.value: [
                'manage_assets',
                'view_assets',
                'manage_tasks',
                'view_logs',
                'manage_backups'
            ],
            UserRole.VIEWER.value: [
                'view_assets',
                'view_tasks',
                'view_logs'
            ]
        }
        return permission in role_permissions.get(self.role, [])

    def set_password(self, password):
        """设置用户密码"""
        self.password_hash = generate_password_hash(password)

class SystemLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    level = db.Column(db.String(20))
    type = db.Column(db.String(50))
    message = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    schedule = db.Column(db.String(100))  # cron 表达式
    command = db.Column(db.Text)
    active = db.Column(db.Boolean, default=True)
    last_run = db.Column(db.DateTime)
    next_run = db.Column(db.DateTime)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Asset(db.Model):
    __tablename__ = 'assets'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    ip_address = db.Column(db.String(15), unique=True, nullable=False)
    type = db.Column(db.String(50))
    status = db.Column(db.String(20), default='unknown')
    os_type = db.Column(db.String(50))
    os_version = db.Column(db.String(50))
    cpu_cores = db.Column(db.Integer)
    memory_size = db.Column(db.Float)
    disk_size = db.Column(db.Float)
    description = db.Column(db.Text)
    specs = db.Column(db.JSON)
    open_ports = db.Column(db.JSON)
    services = db.Column(db.JSON)
    response_time = db.Column(db.Float)
    last_check = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Asset {self.name} ({self.ip_address})>'

class Backup(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(50))
    source = db.Column(db.String(200))
    destination = db.Column(db.String(200))
    schedule = db.Column(db.String(100))  # cron 表达式
    last_backup = db.Column(db.DateTime)
    next_backup = db.Column(db.DateTime)
    status = db.Column(db.String(20))
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class MonitorData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    type = db.Column(db.String(50))  # cpu, memory, disk, network
    metric = db.Column(db.String(50))  # usage, bytes_sent, bytes_recv, etc.
    value = db.Column(db.Float)
    
    def __repr__(self):
        return f'<MonitorData {self.type}.{self.metric}: {self.value}>'

class ProcessData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    pid = db.Column(db.Integer)
    name = db.Column(db.String(100))
    cpu_percent = db.Column(db.Float)
    memory_percent = db.Column(db.Float)
    status = db.Column(db.String(20)) 

class TaskExecution(db.Model):
    """任务执行记录"""
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.String(50), nullable=False)
    scheduled_time = db.Column(db.DateTime, nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    execution_time = db.Column(db.Float, nullable=False)  # 执行时间（秒）
    success = db.Column(db.Boolean, default=True)
    error_message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<TaskExecution {self.job_id} ({self.execution_time:.2f}s)>' 

class MetricAlert(db.Model):
    """监控指标告警规则"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    metric_type = db.Column(db.String(50))  # cpu, memory, disk, network
    metric_name = db.Column(db.String(50))  # usage, bytes_sent等
    condition = db.Column(db.String(20))  # >, <, >=, <=, ==
    threshold = db.Column(db.Float)
    duration = db.Column(db.Integer)  # 持续时间(秒)
    severity = db.Column(db.String(20))  # info, warning, error, critical
    enabled = db.Column(db.Boolean, default=True)
    notify_channels = db.Column(db.JSON)  # email, sms, webhook等
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class AnalysisReport(db.Model):
    """分析报告"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    report_type = db.Column(db.String(50))  # performance, security, resource等
    content = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))

class AutomationRule(db.Model):
    """自动化规则"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    trigger_type = db.Column(db.String(50))  # metric, event, schedule
    trigger_condition = db.Column(db.JSON)
    actions = db.Column(db.JSON)
    enabled = db.Column(db.Boolean, default=True)
    last_triggered = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow) 