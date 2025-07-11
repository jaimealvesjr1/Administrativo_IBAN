from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from .forms import LoginForm, MembroRegistrationForm
from .models import User
from app.extensions import db, login_manager
from app.membresia.models import Membro
from werkzeug.security import generate_password_hash
from config import Config

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('membresia.index'))
        else:
            flash('Usuário ou senha inválidos.', 'warning')
    return render_template('auth/login.html', form=form, ano=Config.ANO_ATUAL, versao=Config.VERSAO_APP)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Você foi desconectado.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/registrar_membro', methods=['GET', 'POST'])
def registrar_membro():
    form = MembroRegistrationForm()
    if form.validate_on_submit():
        user = User(
            email=form.email.data,
            membro_id=form.membro_id.data,
            permissions='membro'
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Conta foi criada com sucesso! Agora você pode fazer login.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/registrar_membro.html', form=form, ano=Config.ANO_ATUAL, versao=Config.VERSAO_APP)
