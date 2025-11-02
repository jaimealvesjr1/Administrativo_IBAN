from app.extensions import db
from datetime import datetime, date, timedelta
from sqlalchemy.orm import relationship
from app.membresia.models import Membro
from sqlalchemy import func
from app.financeiro.models import Contribuicao

area_supervisores = db.Table('area_supervisores',
    db.Column('area_id', db.Integer, db.ForeignKey('area.id'), primary_key=True),
    db.Column('supervisor_id', db.Integer, db.ForeignKey('membro.id'), primary_key=True))

setor_supervisores = db.Table('setor_supervisores',
    db.Column('setor_id', db.Integer, db.ForeignKey('setor.id'), primary_key=True),
    db.Column('supervisor_id', db.Integer, db.ForeignKey('membro.id'), primary_key=True))

class AreaMetaVigente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data_inicio = db.Column(db.Date, default=date.today)
    data_fim = db.Column(db.Date, nullable=False)
    ativa = db.Column(db.Boolean, default=True)
    area_id = db.Column(db.Integer, db.ForeignKey('area.id'), nullable=False)

    meta_facilitadores_treinamento_pg = db.Column(db.Integer, default=0)
    meta_anfitrioes_treinamento_pg = db.Column(db.Integer, default=0)
    meta_ctm_participantes_pg = db.Column(db.Integer, default=0)
    meta_encontro_deus_participantes_pg = db.Column(db.Integer, default=0)
    meta_batizados_aclamados_pg = db.Column(db.Integer, default=0)
    meta_multiplicacoes_pg_pg = db.Column(db.Integer, default=0)

class Area(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(80), unique=True, nullable=False)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)

    supervisores = relationship('Membro', secondary=area_supervisores, back_populates='areas_supervisionadas')
    setores = db.relationship('Setor', backref='area', lazy='dynamic', cascade='all, delete-orphan')

    metas_vigentes = db.relationship('AreaMetaVigente', backref='area', lazy=True, cascade='all, delete-orphan')

    @property
    def meta_vigente(self):
        return AreaMetaVigente.query.filter_by(area_id=self.id).order_by(AreaMetaVigente.data_inicio.desc()).first()

class Setor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(80), unique=True, nullable=False)
    area_id = db.Column(db.Integer, db.ForeignKey('area.id'), nullable=False)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)

    supervisores = relationship('Membro', secondary=setor_supervisores, back_populates='setores_supervisionados')
    pequenos_grupos = db.relationship('PequenoGrupo', backref='setor', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Setor: {self.nome} | Área: {self.area.nome}>'

class PequenoGrupo(db.Model):
    __tablename__ = 'pequeno_grupo'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), unique=True, nullable=False)
    facilitador_id = db.Column(db.Integer, db.ForeignKey('membro.id'), nullable=False)
    anfitriao_id = db.Column(db.Integer, db.ForeignKey('membro.id'), nullable=False)
    setor_id = db.Column(db.Integer, db.ForeignKey('setor.id'), nullable=False)
    dia_reuniao = db.Column(db.String(20), nullable=False)
    horario_reuniao = db.Column(db.String(10), nullable=False)
    data_multiplicacao = db.Column(db.DateTime, nullable=True)
    autorizacao_multiplicacao = db.Column(db.Boolean, default=False)
    ativo = db.Column(db.Boolean, default=True)

    facilitador = db.relationship('Membro', foreign_keys=[facilitador_id], back_populates='pgs_facilitados')
    anfitriao = db.relationship('Membro', foreign_keys=[anfitriao_id], back_populates='pgs_anfitriados')
    participantes = db.relationship('Membro', foreign_keys='Membro.pg_id', back_populates='pg_participante', lazy='dynamic')
    
    def __repr__(self):
        return f'<PG: {self.nome} | Facilitador: {self.facilitador.nome_completo}>'
