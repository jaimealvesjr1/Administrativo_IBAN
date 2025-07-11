from app.extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    
    permissions = db.Column(db.String(255), default='membro_basico') 
    
    membro_id = db.Column(db.Integer, db.ForeignKey('membro.id'), unique=True, nullable=True) 
    membro = db.relationship('Membro', backref='user_account', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def has_permission(self, permission_name):
        if self.permissions is None:
            return False
        return permission_name in self.permissions.split(',')

    def __repr__(self):
        return f'<User {self.email}>'
