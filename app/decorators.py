from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user
from app.grupos.models import Area, Setor, PequenoGrupo

def permission_required(permission_name):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated or not current_user.has_permission(permission_name):
                flash('Você não tem permissão para acessar aqui.', 'danger')
                return redirect(url_for('main.index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.has_permission('admin'):
            flash('Você não tem permissão de administrador para acessar esta página.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

def financeiro_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.has_permission('financeiro') and not current_user.has_permission('admin'):
            flash('Você não tem permissão de tesoureiro para acessar esta página.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

def leader_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_leader():
            flash('Você não tem permissão de liderança para acessar esta página.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

def group_permission_required(model, action):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            entity_id = kwargs.get('area_id') or kwargs.get('setor_id') or kwargs.get('pg_id')
            if not entity_id:
                flash('ID não fornecido.', 'danger')
                return redirect(url_for('main.index'))

            entity = model.query.get(entity_id)
            if not entity:
                flash('Grupo não encontrado.', 'danger')
                return redirect(url_for('main.index'))

            if not current_user.is_authenticated or not current_user.has_group_permission(entity, action):
                flash('Você não tem permissão para realizar esta ação.', 'danger')
                return redirect(url_for('main.index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator
