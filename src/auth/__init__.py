from flask_login import LoginManager
from werkzeug.security import generate_password_hash, check_password_hash
from src.models import User, db

login_manager = LoginManager()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def init_auth(app):
    login_manager.init_app(app)
    login_manager.login_view = 'main.login'

def create_user(username, password, role='viewer'):
    user = User(
        username=username,
        password_hash=generate_password_hash(password),
        role=role
    )
    db.session.add(user)
    db.session.commit()
    return user

def verify_password(user, password):
    return check_password_hash(user.password_hash, password) 