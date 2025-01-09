from flask import Flask
from flask_login import LoginManager
from src.models import db, User
from src.auth import init_auth
from src.scheduler import init_scheduler
from src.backup import BackupManager
from src.assets import AssetManager
from src.monitor.system_monitor import SystemMonitor
from pytz import timezone
import logging
import os
from src.web.auth import auth_bp
from src.web.routes import main_bp, api_bp
from sqlalchemy.sql import text
from sqlalchemy import text

def create_app(config=None):
    app = Flask(__name__)
    
    # 配置应用
    if config is None:
        # 使用默认配置
        app.config.from_object('src.config.default')
    else:
        # 更新配置
        if isinstance(config, dict):
            # 设置数据库URI
            if config.get('database', {}).get('type') == 'mysql':
                db_config = config['database']['mysql']
                app.config['SQLALCHEMY_DATABASE_URI'] = (
                    f"mysql+pymysql://{db_config['username']}:{db_config['password']}"
                    f"@{db_config['host']}:{db_config['port']}/{db_config['database']}?charset=utf8mb4"
                )
            else:
                app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///data/app.db"
            
            # 其他配置
            app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
            app.config['SECRET_KEY'] = config.get('security', {}).get('secret_key', 'dev')
            app.config['PERMANENT_SESSION_LIFETIME'] = config.get('security', {}).get('session_lifetime', 3600)
            app.config['SCHEDULER_TIMEZONE'] = config.get('scheduler', {}).get('timezone', 'UTC')
            
            # 配置日志
            log_config = config.get('logging', {})
            log_level = getattr(logging, log_config.get('level', 'INFO'))
            log_file = log_config.get('file', 'data/app.log')
            log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            
            # 确保日志目录存在
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            
            # 配置日志处理器
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(logging.Formatter(log_format))
            
            # 配置根日志记录器
            root_logger = logging.getLogger()
            root_logger.setLevel(log_level)
            root_logger.addHandler(file_handler)
            
            # 配置 Flask 应用日志记录器
            app.logger.setLevel(log_level)
            if not app.debug:
                app.logger.addHandler(file_handler)
            
            app.config.update(config)
        else:
            app.config.from_object(config)
    
    # 确保必要的配置存在
    app.config.setdefault('SQLALCHEMY_DATABASE_URI', 'sqlite:///data/app.db')
    app.config.setdefault('SQLALCHEMY_TRACK_MODIFICATIONS', False)
    app.config.setdefault('SECRET_KEY', 'dev')
    app.config.setdefault('SCHEDULER_TIMEZONE', 'UTC')
    
    app.config.setdefault('MONITOR', {
        'check_interval': 300,  # 5分钟
        'thresholds': {
            'cpu_percent': 80,
            'memory_usage': 85,
            'disk_usage': 90,
            'bytes_sent': 1000000000,
            'bytes_recv': 1000000000
        },
        'retention_days': 30
    })
    
    # 添加 CSRF 保护
    app.config['WTF_CSRF_SECRET_KEY'] = app.config.get('SECRET_KEY', 'dev')
    
    # 初始化数据库
    db.init_app(app)
    
    # 创建数据库表
    with app.app_context():
        try:
            # 确保数据目录存在
            if app.config['SQLALCHEMY_DATABASE_URI'].startswith('sqlite'):
                db_path = os.path.dirname(app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', ''))
                os.makedirs(db_path, exist_ok=True)
            
            # 删除旧表
            app.logger.info("Dropping all tables...")
            db.drop_all()
            db.session.commit()
            
            # 创建新表
            app.logger.info("Creating all tables...")
            db.create_all()
            
            # 如果是 MySQL，修改密码哈希字段长度
            if 'mysql' in app.config['SQLALCHEMY_DATABASE_URI']:
                app.logger.info("Altering password_hash column length...")
                db.session.execute(text(
                    "ALTER TABLE user MODIFY COLUMN password_hash VARCHAR(512) "
                    "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL"
                ))
            
            db.session.commit()
            
            # 检查表是否正确创建
            app.logger.info("Checking database schema...")
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            app.logger.info(f"Created tables: {tables}")
            
            # 检查用户表结构
            app.logger.info("Checking user table schema...")
            user_table = 'user'  # 使用确定的表名
            if user_table not in tables:
                app.logger.error(f"User table '{user_table}' was not created!")
                app.logger.error(f"Available tables: {tables}")
                raise Exception(f"Database initialization failed: {user_table} table not found")
            
            # 检查列是否存在
            columns = [col['name'] for col in inspector.get_columns(user_table)]
            app.logger.info(f"User table columns: {columns}")
            
            expected_columns = ['id', 'username', 'password_hash', 'role', 'active', 'last_login', 'created_at']
            missing_columns = [col for col in expected_columns if col not in columns]
            
            if missing_columns:
                app.logger.error(f"Missing columns in user table: {missing_columns}")
                app.logger.error(f"Available columns: {columns}")
                raise Exception(f"Database schema is incorrect: missing columns {missing_columns}")
            
            # 创建默认管理员用户
            app.logger.info("Creating admin user...")
            if not User.query.filter_by(username='admin').first():
                from werkzeug.security import generate_password_hash
                admin = User()
                admin.username = 'admin'
                admin.password_hash = generate_password_hash('admin')
                admin.role = 'admin'  # 设置角色为管理员
                admin.active = True   # 设置为活动状态
                
                db.session.add(admin)
                try:
                    db.session.commit()
                    app.logger.info('Created default admin user successfully')
                except Exception as e:
                    db.session.rollback()
                    app.logger.error(f'Failed to create admin user: {e}')
                    raise
            
            app.logger.info("Database initialization completed successfully")
            
        except Exception as e:
            app.logger.error(f"Database initialization failed: {str(e)}", exc_info=True)
            raise Exception(f"Database initialization failed: {str(e)}")
    
    # 初始化认证
    init_auth(app)
    
    # 初始化系统监控
    app.config['monitor'] = SystemMonitor(app.config['MONITOR'])
    
    # 初始化任务调度器
    init_scheduler(app)
    
    # 初始化备份管理器
    app.backup_manager = BackupManager(config)
    
    # 初始化资产管理器
    app.asset_manager = AssetManager()
    
    # 初始化 Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = '请先登录'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # 注册蓝图
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)
    
    # 在 create_app 函数中添加控制台日志处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(log_format))
    root_logger.addHandler(console_handler)
    
    return app 