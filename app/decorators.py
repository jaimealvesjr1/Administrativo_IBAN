from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user

def permission_required(permission_name):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated or not current_user.has_permission(permission_name):
                flash(f'Você não tem permissão para acessar esta página.', 'danger')
                return redirect(url_for('main.index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def admin_required(f):
    return permission_required('admin')(f)

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

def group_permission_required(model, permission, relationship_name=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if current_user.has_permission('admin'):
                return f(*args, **kwargs)

            group_id = kwargs.get(f'{model.__tablename__.lower()}_id')
            if not group_id:
                flash('Não foi possível encontrar o ID do grupo.', 'danger')
                return redirect(url_for('main.index'))

            group_obj = model.query.get_or_404(group_id)

            if not current_user.membro:
                flash(f'Você não tem permissão de {permission} neste grupo.', 'danger')
                return redirect(url_for('main.index'))
            
            if relationship_name:
                supervisores = getattr(group_obj, relationship_name, None)
                if supervisores and current_user.membro in supervisores:
                    return f(*args, **kwargs)
            
            if model.__name__ == 'PequenoGrupo':
                is_facilitador = current_user.membro.id == group_obj.facilitador_id
                is_anfitriao = current_user.membro.id == group_obj.anfitriao_id
                
                if permission == 'view' and (is_facilitador or is_anfitriao):
                    return f(*args, **kwargs)
                if permission == 'edit' and is_facilitador:
                    return f(*args, **kwargs)
                if permission == 'manage_participants' and (is_facilitador or is_anfitriao):
                    return f(*args, **kwargs)
            
            flash(f'Você não tem permissão de {permission} neste grupo.', 'danger')
            return redirect(url_for('main.index'))
        return decorated_function
    return decorator
