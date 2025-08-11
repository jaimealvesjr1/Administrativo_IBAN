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
    membro = db.relationship('Membro', backref='user_account', lazy=True)

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
        if self.has_permission('admin'):
            return True
        if not self.membro:
            return False
            
        return (self.membro.areas_coordenadas.first() is not None or
                self.membro.setores_supervisionados.first() is not None or
                self.membro.pgs_facilitados.first() is not None or
                self.membro.pgs_anfitriados.first() is not None)


    def has_group_permission(self, entity, action):
        if self.has_permission('admin'):
            return True
            
        if not self.membro:
            return False

        membro_logado = self.membro

        # Permissões para ÁREA
        if isinstance(entity, Area):
            # Coordenador da área tem todas as permissões sobre sua área
            if entity.coordenador_id == membro_logado.id:
                return True
            return False

        # Permissões para SETOR
        if isinstance(entity, Setor):
            # Supervisor do setor tem todas as permissões sobre seu setor
            if entity.supervisor_id == membro_logado.id:
                return True
            # Coordenador da área pai pode editar ou visualizar
            if entity.area and entity.area.coordenador_id == membro_logado.id:
                # Coordenador pode editar e gerenciar metas de setores abaixo dele
                if action in ['edit', 'manage_metas_setor', 'view']:
                    return True
            return False

        # Permissões para PEQUENO GRUPO
        if isinstance(entity, PequenoGrupo):
            # Facilitador pode ver, editar, gerenciar participantes e metas
            if entity.facilitador_id == membro_logado.id:
                if action in ['view', 'edit', 'manage_participants', 'manage_metas_pg']:
                    return True
            # Anfitrião pode ver e gerenciar participantes e metas
            if entity.anfitriao_id == membro_logado.id:
                if action in ['view', 'manage_participants', 'manage_metas_pg']:
                    return True
            # Supervisor do setor pai pode ver, editar, gerenciar participantes e metas
            if entity.setor and entity.setor.supervisor_id == membro_logado.id:
                if action in ['view', 'edit', 'manage_participants', 'manage_metas_pg']:
                    return True
            # Coordenador da área pai pode apenas visualizar
            if action == 'view' and entity.setor and entity.setor.area and entity.setor.area.coordenador_id == membro_logado.id:
                return True
            return False
        
        # Permissões para MEMBRO (perfil individual)
        if isinstance(entity, Membro):
            # O próprio membro pode ver seu perfil
            if entity.id == membro_logado.id:
                return True
            # Facilitador/Anfitrião podem ver os participantes do seu PG
            if membro_logado.pgs_facilitados.filter_by(id=entity.pg_id).first() or \
               membro_logado.pgs_anfitriados.filter_by(id=entity.pg_id).first():
                return True
            # Supervisor pode ver membros dos PGs de seu setor
            for setor in membro_logado.setores_supervisionados:
                if entity.pg_participante in setor.pequenos_grupos.with_parent(setor).all():
                    return True
            # Coordenador pode ver membros dos PGs de sua área
            for area in membro_logado.areas_coordenadas:
                for setor in area.setores:
                    if entity.pg_participante in setor.pequenos_grupos.with_parent(setor).all():
                        return True
            return False
            
        return False

    def __repr__(self):
        return f'<User {self.email}>'
    