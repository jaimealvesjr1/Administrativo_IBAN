from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required
from .forms import LoginForm
from .models import User
from app.extensions import db, login_manager
from config import Config

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')
ano=Config.ANO_ATUAL,
versao=Config.VERSAO_APP

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            return redirect(url_for('membresia.index'))
        else:
            flash('Usuário ou senha inválidos.', 'warning')
    return render_template('auth/login.html',
                           form=form,ano=ano, versao=versao)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
