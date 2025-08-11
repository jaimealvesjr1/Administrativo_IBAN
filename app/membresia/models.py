from app.extensions import db
from datetime import datetime, date, timedelta
from sqlalchemy import String, func
from flask import url_for

class Membro(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    foto_perfil = db.Column(db.String(255), nullable=True, default='default.jpg')
    nome_completo = db.Column(db.String(120), nullable=False)
    data_nascimento = db.Column(db.Date, nullable=True)
    data_recepcao = db.Column(db.Date, nullable=True)
    tipo_recepcao = db.Column(db.String(50), nullable=False)
    obs_recepcao = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), nullable=False)
    campus = db.Column(db.String(50), nullable=False)
    ativo = db.Column(db.Boolean, default=True)

    pg_id = db.Column(db.Integer, db.ForeignKey('pequeno_grupo.id'), nullable=True)
    status_treinamento_pg = db.Column(db.String(50), nullable=False, default='Participante')
    participou_ctm = db.Column(db.Boolean, nullable=False, default=False)
    participou_encontro_deus = db.Column(db.Boolean, nullable=False, default=False)
    batizado_aclamado = db.Column(db.Boolean, nullable=False, default=False)
    campus_frequencia = db.Column(db.String(50), nullable=True)

    presencas = db.relationship('Presenca', backref='membro', lazy=True)

    areas_coordenadas = db.relationship('Area', back_populates='coordenador', lazy='dynamic', foreign_keys='Area.coordenador_id')
    setores_supervisionados = db.relationship('Setor', back_populates='supervisor', lazy='dynamic', foreign_keys='Setor.supervisor_id')
    pgs_facilitados = db.relationship('PequenoGrupo', back_populates='facilitador', lazy='dynamic', foreign_keys='PequenoGrupo.facilitador_id')
    pgs_anfitriados = db.relationship('PequenoGrupo', back_populates='anfitriao', lazy='dynamic', foreign_keys='PequenoGrupo.anfitriao_id')

    @property
    def contribuiu_dizimo_mes_atual(self):
        from app.financeiro.models import Contribuicao
        mes_atual = date.today().month
        ano_atual = date.today().year
        return db.session.query(Contribuicao).filter(
            Contribuicao.membro_id == self.id,
            Contribuicao.tipo == 'Dízimo',
            Contribuicao.data_lanc.like(f'{ano_atual}-{str(mes_atual).zfill(2)}%')
        ).first() is not None

    @property
    def contribuiu_dizimo_ultimos_30d(self):
        from app.financeiro.models import Contribuicao
        hoje = datetime.now()
        trinta_dias_atras = hoje - timedelta(days=30)
        return db.session.query(Contribuicao.id).filter(
            Contribuicao.membro_id == self.id,
            Contribuicao.tipo == 'Dízimo',
            Contribuicao.data_lanc >= trinta_dias_atras
        ).first() is not None

    def __repr__(self):
        return f'<Membro {self.nome_completo}>'

    def get_cargo_lideranca(self):
        if self.areas_coordenadas.first():
            return f"Coordenador da Área {self.areas_coordenadas.first().nome}"
        
        if self.setores_supervisionados.first():
            return f"Supervisor do Setor {self.setores_supervisionados.first().nome}"
            
        if self.pgs_facilitados.first():
            return f"Facilitador do PG {self.pgs_facilitados.first().nome}"

        if self.pgs_anfitriados.first():
            return f"Anfitrião do PG {self.pgs_anfitriados.first().nome}"

        return None

    def get_foto_perfil_url(self):
        return url_for('static', filename=f'uploads/profile_pics/{self.foto_perfil}')
