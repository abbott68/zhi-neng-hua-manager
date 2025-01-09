from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from src.models import User, db, UserRole
from werkzeug.security import check_password_hash, generate_password_hash
from src.web.forms import LoginForm, RegisterForm
from functools import wraps
from flask import abort

auth_bp = Blueprint('auth', __name__)

def permission_required(permission):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.has_permission(permission):
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password_hash, form.password.data):
            login_user(user)
            return redirect(url_for('main.index'))
        else:
            flash('用户名或密码错误', 'danger')
    
    return render_template('login.html', form=form)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
        
    form = RegisterForm()
    if form.validate_on_submit():
        # 检查是否已存在管理员（第一个注册的用户自动成为管理员）
        if User.query.filter_by(role=UserRole.ADMIN.value).first() is None:
            role = UserRole.ADMIN.value
        else:
            role = form.role.data
            
        # 创建新用户
        user = User(
            username=form.username.data,
            email=form.email.data,
            role=role,
            department=form.department.data
        )
        user.set_password(form.password.data)
        
        try:
            db.session.add(user)
            db.session.commit()
            flash('注册成功！请等待管理员审核。', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            flash('注册失败：' + str(e), 'danger')
            
    return render_template('auth/register.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login')) 