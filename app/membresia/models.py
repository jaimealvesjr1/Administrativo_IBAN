from app.extensions import db
from datetime import datetime, date, timedelta
from sqlalchemy import String, func
from sqlalchemy.orm import relationship
from flask import url_for
from app.ctm.models import Presenca, AulaRealizada

class Membro(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    foto_perfil = db.Column(db.String(255), nullable=True, default='default.jpg')
    nome_completo = db.Column(db.String(120), nullable=False)
    data_nascimento = db.Column(db.Date, nullable=True)

    status = db.Column(db.String(50), nullable=False)

    data_recepcao = db.Column(db.Date, nullable=True)
    tipo_recepcao = db.Column(db.String(50), nullable=True)
    obs_recepcao = db.Column(db.Text, nullable=True)

    campus = db.Column(db.String(50), nullable=False)
    ativo = db.Column(db.Boolean, default=True)

    pg_id = db.Column(db.Integer, db.ForeignKey('pequeno_grupo.id'), nullable=True)
    status_treinamento_pg = db.Column(db.String(50), nullable=False, default='Participante')
    participou_ctm = db.Column(db.Boolean, nullable=False, default=False)
    participou_encontro_deus = db.Column(db.Boolean, nullable=False, default=False)
    batizado_aclamado = db.Column(db.Boolean, nullable=False, default=False)

    presencas = db.relationship('Presenca', backref='membro', lazy=True)
    pg_participante = relationship('PequenoGrupo', back_populates='participantes', foreign_keys='Membro.pg_id')
    
    areas_supervisionadas = relationship('Area', secondary='area_supervisores', back_populates='supervisores')
    setores_supervisionados = relationship('Setor', secondary='setor_supervisores', back_populates='supervisores')
    pgs_facilitados = relationship('PequenoGrupo', back_populates='facilitador', foreign_keys='PequenoGrupo.facilitador_id')
    pgs_anfitriados = relationship('PequenoGrupo', back_populates='anfitriao', foreign_keys='PequenoGrupo.anfitriao_id')

    user = db.relationship('User', back_populates='membro', uselist=False)

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
        hoje = date.today()
        trinta_dias_atras = hoje - timedelta(days=35)
        return db.session.query(Contribuicao.id).filter(
            Contribuicao.membro_id == self.id,
            Contribuicao.tipo == 'Dízimo',
            Contribuicao.data_lanc >= trinta_dias_atras
        ).first() is not None

    @property
    def presente_ctm_ultimos_30d(self):
        trinta_dias_atras = date.today() - timedelta(days=35)
        return db.session.query(Presenca).join(AulaRealizada).filter(
            Presenca.membro_id == self.id,
            AulaRealizada.data >= trinta_dias_atras
        ).first() is not None

    def __repr__(self):
        return f'<Membro {self.nome_completo}>'

    def get_cargo_lideranca(self):
        areas = [f"Supervisor da Área {a.nome}" for a in self.areas_supervisionadas]
        setores = [f"Supervisor do Setor {s.nome}" for s in self.setores_supervisionados]
        pgs_facilitados = [f"Facilitador do PG {p.nome}" for p in self.pgs_facilitados]
        pgs_anfitriados = [f"Anfitrião do PG {p.nome}" for p in self.pgs_anfitriados]
        
        cargos = areas + setores + pgs_facilitados + pgs_anfitriados
        
        if cargos:
            return ", ".join(cargos)
        
        return "Nenhum"

    def get_foto_perfil_url(self):
        return url_for('static', filename=f'uploads/profile_pics/{self.foto_perfil}')

    @property
    def status_exibicao(self):
        """Retorna o status mais relevante do membro para exibição."""
        cargo = self.get_cargo_lideranca()
        if cargo:
            return cargo

        if self.pg_participante and self.status_treinamento_pg:
            if self.status_treinamento_pg:
                return self.status_treinamento_pg

        if self.status in ['Membro', 'Não-Membro']:
            return self.status
                
        return 'Não-Membro'
