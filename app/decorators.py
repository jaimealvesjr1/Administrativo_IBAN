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

def secretaria_or_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.has_permission('secretaria') and not current_user.has_permission('admin'):
            flash('Você não tem permissão de secretário para acessar esta página.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

def leader_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.is_authenticated and (
            current_user.has_permission('admin') or
            current_user.has_permission('secretaria') or
            current_user.is_leader()
        ):
            return f(*args, **kwargs)

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
            
            if current_user.has_permission('secretaria'):
                return f(*args, **kwargs)

            if not current_user.membro:
                flash(f'Você não tem permissão de {permission} neste grupo.', 'danger')
                return redirect(url_for('main.index'))
            
            group_id = kwargs.get(f'{model.__tablename__.lower()}_id') or \
                       kwargs.get(f'{model.__tablename__.lower().replace("_", "")}_id')
            
            if not group_id:
                if model.__name__ == 'PequenoGrupo':
                    group_id = kwargs.get('pg_id')
                elif model.__name__ == 'Setor':
                    group_id = kwargs.get('setor_id')
                elif model.__name__ == 'Area':
                    group_id = kwargs.get('area_id')

            if not group_id:
                flash('Não foi possível encontrar o ID do grupo.', 'danger')
                return redirect(url_for('main.index'))

            group_obj = model.query.get_or_404(group_id)

            def check_hierarchy(obj, user_membro):
                if not obj:
                    return False
                
                if obj.__tablename__ == 'pequeno_grupo':
                    if user_membro.id == obj.facilitador_id or user_membro.id == obj.anfitriao_id:
                        return True
                    return check_hierarchy(obj.setor, user_membro)

                elif obj.__tablename__ == 'setor':
                    if user_membro in obj.supervisores:
                        return True
                    return check_hierarchy(obj.area, user_membro)

                elif obj.__tablename__ == 'area':
                    if user_membro in obj.supervisores:
                        return True
                
                return False

            if check_hierarchy(group_obj, current_user.membro):
                return f(*args, **kwargs)
            
            flash(f'Você não tem permissão de {permission} neste grupo.', 'danger')
            return redirect(url_for('main.index'))
        return decorated_function
    return decorator
