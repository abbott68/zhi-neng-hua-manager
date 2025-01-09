from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from src.models import db, User
import os
import logging
from logging.handlers import RotatingFileHandler
from apscheduler.schedulers.background import BackgroundScheduler
import atexit
import psutil
from datetime import datetime
import yaml

def load_config():
    """加载配置文件"""
    with open('config.yml', 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def create_app():
    app = Flask(__name__)
    
    # 加载配置
    config = load_config()
    
    # 配置
    app.config['SECRET_KEY'] = config['app']['secret_key']
    app.config['SQLALCHEMY_DATABASE_URI'] = config['database']['url']
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = config['database']['track_modifications']
    
    # 初始化扩展
    db.init_app(app)
    migrate = Migrate(app, db)
    
    # 设置登录管理
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # 注册蓝图
    from src.web.routes import main_bp, api_bp
    from src.web.auth import auth_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(auth_bp)
    
    # 设置日志
    if not os.path.exists('logs'):
        os.mkdir('logs')
    
    file_handler = RotatingFileHandler(
        config['logging']['file'],
        maxBytes=config['logging']['max_size'],
        backupCount=config['logging']['backup_count']
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('应用启动')
    
    # 初始化数据库
    with app.app_context():
        db.create_all()
        
        # 创建默认管理员用户（如果不存在）
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                email='admin@example.com',
                role='admin'
            )
            admin.set_password('admin')
            db.session.add(admin)
            db.session.commit()
    
    return app

def init_scheduler(app):
    """初始化定时任务"""
    scheduler = BackgroundScheduler()
    
    def collect_metrics_job():
        """收集系统指标"""
        with app.app_context():
            from src.models import MonitorData, db
            
            # 收集系统指标
            cpu_percent = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # 保存到数据库
            metrics = MonitorData(
                type='system',
                metric='cpu_usage',
                value=cpu_percent
            )
            db.session.add(metrics)
            
            metrics = MonitorData(
                type='system',
                metric='memory_usage',
                value=memory.percent
            )
            db.session.add(metrics)
            
            metrics = MonitorData(
                type='system',
                metric='disk_usage',
                value=disk.percent
            )
            db.session.add(metrics)
            
            db.session.commit()
    
    # 添加定时任务
    scheduler.add_job(
        func=collect_metrics_job,
        trigger='interval',
        minutes=5,
        id='collect_metrics_job'
    )
    
    scheduler.start()
    atexit.register(lambda: scheduler.shutdown())

if __name__ == '__main__':
    app = create_app()
    init_scheduler(app)
    app.run(debug=True) 