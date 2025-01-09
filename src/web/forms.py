from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, EmailField
from wtforms.validators import DataRequired, Email, Length, EqualTo

class LoginForm(FlaskForm):
    """登录表单"""
    username = StringField('用户名', validators=[DataRequired()])
    password = PasswordField('密码', validators=[DataRequired()])

class RegisterForm(FlaskForm):
    """注册表单"""
    username = StringField('用户名', validators=[
        DataRequired(), 
        Length(min=4, max=20, message='用户名长度必须在4-20个字符之间')
    ])
    email = EmailField('邮箱', validators=[
        DataRequired(), 
        Email(message='请输入有效的邮箱地址')
    ])
    password = PasswordField('密码', validators=[
        DataRequired(), 
        Length(min=6, message='密码长度不能少于6个字符')
    ])
    confirm_password = PasswordField('确认密码', validators=[
        DataRequired(),
        EqualTo('password', message='两次输入的密码不一致')
    ])
    role = SelectField('角色', choices=[
        ('viewer', '只读用户'),
        ('operator', '运维人员'),
        ('admin', '管理员')
    ])
    department = StringField('部门', validators=[DataRequired()]) 