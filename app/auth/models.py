from app.extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.membresia.models import Membro
from app.grupos.models import Area, Setor, PequenoGrupo

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    
    permissions = db.Column(db.String(255), default='membro') 
    
    membro_id = db.Column(db.Integer, db.ForeignKey('membro.id'), unique=True, nullable=True) 
    membro = db.relationship('Membro', back_populates='user')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def has_permission(self, permission_name):
        if self.permissions is None:
            return False
        permissions_list = self.permissions.split(',')
        if 'admin' in permissions_list:
            return True
        return permission_name in permissions_list

    def is_leader(self):
        if not self.membro:
            return False
            
        return (len(self.membro.areas_supervisionadas) > 0 or
                len(self.membro.setores_supervisionados) > 0 or
                len(self.membro.pgs_facilitados) > 0 or
                len(self.membro.pgs_anfitriados) > 0)

    def has_group_permission(self, entity, action):
        if self.has_permission('admin'):
            return True
            
        if not self.membro:
            return False

        membro_logado = self.membro

        if isinstance(entity, Area):
            if membro_logado in entity.supervisores:
                return True
            return False

        if isinstance(entity, Setor):
            if membro_logado in entity.supervisores:
                return True
            if entity.area and membro_logado in entity.area.supervisores:
                if action in ['edit', 'manage_metas_setor', 'view']:
                    return True
            return False

        if isinstance(entity, PequenoGrupo):
            if entity.facilitador_id == membro_logado.id:
                if action in ['view', 'edit', 'manage_participants', 'manage_metas_pg']:
                    return True
            if entity.anfitriao_id == membro_logado.id:
                if action in ['view', 'manage_participants', 'manage_metas_pg']:
                    return True
            if entity.setor and membro_logado in entity.setor.supervisores:
                if action in ['view', 'edit', 'manage_participants', 'manage_metas_pg']:
                    return True
            if action == 'view' and entity.setor and entity.setor.area and membro_logado in entity.setor.area.supervisores:
                return True
            return False
        
        if isinstance(entity, Membro):
            if entity.id == membro_logado.id:
                return True
            if membro_logado.pgs_facilitados.filter_by(id=entity.pg_id).first() or \
               membro_logado.pgs_anfitriados.filter_by(id=entity.pg_id).first():
                return True
            for setor in membro_logado.setores_supervisionados:
                if entity.pg_participante in setor.pequenos_grupos.all():
                    return True
            for area in membro_logado.areas_supervisionadas:
                for setor in area.setores:
                    if entity.pg_participante in setor.pequenos_grupos.all():
                        return True
            return False
            
        return False

    def __repr__(self):
        return f'<User {self.email}>'
    