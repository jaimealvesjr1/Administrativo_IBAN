from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.extensions import db
from app.auth.models import User
from app.membresia.models import Membro
from app.decorators import admin_required
from .forms import RequestResetPasswordForm, ResetPasswordForm, UserEditForm
from werkzeug.security import generate_password_hash
from config import Config
import os

admin_users_bp = Blueprint('admin_users', __name__, url_prefix='/admin_users')

def is_admin():
    return current_user.is_authenticated and current_user.has_permission('admin')

@admin_users_bp.before_request
@login_required
def require_admin_permission():
    if not is_admin():
        return redirect(url_for('membresia.index'))

@admin_users_bp.route('/')
def list_users():
    users = User.query.order_by(User.email).all()
    return render_template('admin_users/list_users.html', users=users, ano=Config.ANO_ATUAL, versao=Config.VERSAO_APP)

@admin_users_bp.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    form = UserEditForm(original_email=user.email)

    if form.validate_on_submit():
        user.email = form.email.data

        if form.password.data:
            user.set_password(form.password.data)

        permissions_list = form.permissions.data
        user.permissions = ','.join(permissions_list)

        try:
            db.session.commit()
            flash('Usuário atualizado com sucesso!', 'success')
            return redirect(url_for('admin_users.list_users'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar usuário: {e}', 'danger')

    elif request.method == 'GET':
        form.email.data = user.email
        current_permissions = user.permissions.split(',') if user.permissions else []
        form.permissions.data = current_permissions

    return render_template('admin_users/edit_user.html', form=form, user=user)

@admin_users_bp.route('/<int:user_id>/delete', methods=['POST'])
@login_required
def delete_user(user_id):
    if user_id == current_user.id:
        flash('Você não pode excluir sua própria conta por aqui.', 'danger')
        return redirect(url_for('admin_users.list_users'))

    user = User.query.get_or_404(user_id)
    
    try:
        db.session.delete(user)
        db.session.commit()
        flash(f'Usuário {user.email} excluído com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir usuário: {str(e)}', 'danger')
    
    return redirect(url_for('admin_users.list_users'))

@admin_users_bp.route('/request_reset', methods=['GET', 'POST'])
def request_reset():
    if current_user.is_authenticated:
        return redirect(url_for('membresia.index'))
    form = RequestResetPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            flash('Se uma conta com este email existir, um email com instruções para redefinir a senha foi enviado.', 'info')
        else:
            flash('Se uma conta com este email existir, um email com instruções para redefinir a senha foi enviado.', 'info')
        return redirect(url_for('auth.login'))
    return render_template('admin_users/request_reset.html', form=form, ano=Config.ANO_ATUAL, versao=Config.VERSAO_APP)

@admin_users_bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('membresia.index'))
    user = None
    if user is None:
        flash('Token de redefinição inválido ou expirado.', 'warning')
        return redirect(url_for('admin_users.request_reset'))
    
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash('Sua senha foi redefinida com sucesso! Você pode fazer login agora.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('admin_users/reset_password.html', form=form, ano=Config.ANO_ATUAL, versao=Config.VERSAO_APP)
