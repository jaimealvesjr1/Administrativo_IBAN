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
    data_inicio = db.Column(db.DateTime, default=datetime.utcnow)
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
        return AreaMetaVigente.query.filter_by(area_id=self.id, ativa=True).order_by(AreaMetaVigente.data_inicio.desc()).first()

    @property
    def meta_facilitadores_treinamento(self):
        return self.meta_vigente.meta_facilitadores_treinamento_pg * self.num_pequenos_grupos if self.meta_vigente else 0
    @property
    def meta_anfitrioes_treinamento(self):
        return self.meta_vigente.meta_anfitrioes_treinamento_pg * self.num_pequenos_grupos if self.meta_vigente else 0
    @property
    def meta_ctm_participantes(self):
        return self.meta_vigente.meta_ctm_participantes_pg * self.num_pequenos_grupos if self.meta_vigente else 0
    @property
    def meta_encontro_deus_participantes(self):
        return self.meta_vigente.meta_encontro_deus_participantes_pg * self.num_pequenos_grupos if self.meta_vigente else 0
    @property
    def meta_batizados_aclamados(self):
        return self.meta_vigente.meta_batizados_aclamados_pg * self.num_pequenos_grupos if self.meta_vigente else 0
    @property
    def meta_multiplicacoes_pg(self):
        return self.meta_vigente.meta_multiplicacoes_pg_pg * self.num_pequenos_grupos if self.meta_vigente else 0

    @property
    def num_pequenos_grupos(self):
        count = 0
        for setor in self.setores:
            count += setor.pequenos_grupos.count()
        return count

    @property
    def membros_da_area_completos(self):
        membros = set()
        membros.update(self.supervisores)
        for setor in self.setores.all():
            membros.update(setor.membros_do_setor_completos)
        return list(membros)

    @property
    def num_facilitadores_treinamento_atuais_agregado(self):
        count = sum(setor.num_facilitadores_treinamento_atuais_agregado for setor in self.setores.all())
        count += sum(1 for supervisor in self.supervisores if supervisor.status_treinamento_pg == 'Facilitador em Treinamento')
        return count

    @property
    def num_anfitrioes_treinamento_atuais_agregado(self):
        count = sum(setor.num_anfitrioes_treinamento_atuais_agregado for setor in self.setores.all())
        count += sum(1 for supervisor in self.supervisores if supervisor.status_treinamento_pg == 'Anfitrião em Treinamento')
        return count

    @property
    def num_ctm_participantes_atuais_agregado(self):
        count = sum(setor.num_ctm_participantes_atuais_agregado for setor in self.setores.all())
        count += sum(1 for supervisor in self.supervisores if supervisor.participou_ctm)
        return count

    @property
    def num_encontro_deus_participantes_atuais_agregado(self):
        return sum(setor.num_encontro_deus_participantes_atuais_agregado for setor in self.setores.all())

    @property
    def num_batizados_aclamados_atuais_agregado(self):
        return sum(setor.num_batizados_aclamados_atuais_agregado for setor in self.setores.all())

    @property
    def num_multiplicacoes_pg_atuais_agregado(self):
        if not self.meta_vigente:
            return 0
        
        pgs_multiplicados = 0
        data_inicio_meta = self.meta_vigente.data_inicio
        
        for setor in self.setores.all():
            pgs_multiplicados += setor.pequenos_grupos.filter(PequenoGrupo.data_multiplicacao >= data_inicio_meta).count()
            
        return pgs_multiplicados
    
    @property
    def num_participantes_totais_agregado(self):
        return len(self.membros_da_area_completos)

    @property
    def num_dizimistas_atuais_agregado(self):
        membros_da_area = self.membros_da_area_completos
        return sum(1 for membro in membros_da_area if membro.contribuiu_dizimo_ultimos_30d)

    @property
    def distribuicao_campus_frequencia(self):
        campus_counts = {}
        membros_da_area = self.membros_da_area_completos
        
        for membro in membros_da_area:
            campus = membro.campus if membro.campus else 'Não Informado'
            campus_counts[campus] = campus_counts.get(campus, 0) + 1
        return campus_counts
    
    @property
    def distribuicao_dizimistas_30d(self):
        try:
            membros_da_area = self.membros_da_area_completos
            num_dizimistas = sum(1 for membro in membros_da_area if membro.contribuiu_dizimo_ultimos_30d)
            num_nao_dizimistas = len(membros_da_area) - num_dizimistas
            return {'dizimistas': num_dizimistas, 'nao_dizimistas': num_nao_dizimistas}
        except Exception as e:
            print(f"ERRO ao calcular distribuição de dizimistas: {e}")
            return {'dizimistas': 0, 'nao_dizimistas': 0}

    def __repr__(self):
        return f'<Área: {self.nome}>'

class Setor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(80), unique=True, nullable=False)
    area_id = db.Column(db.Integer, db.ForeignKey('area.id'), nullable=False)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)

    supervisores = relationship('Membro', secondary=setor_supervisores, back_populates='setores_supervisionados')
    pequenos_grupos = db.relationship('PequenoGrupo', backref='setor', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def meta_facilitadores_treinamento(self):
        meta_pg_unitario = self.area.meta_vigente.meta_facilitadores_treinamento_pg if self.area and self.area.meta_vigente else 0
        return meta_pg_unitario * self.pequenos_grupos.count()
    @property
    def meta_anfitrioes_treinamento(self):
        meta_pg_unitario = self.area.meta_vigente.meta_anfitrioes_treinamento_pg if self.area and self.area.meta_vigente else 0
        return meta_pg_unitario * self.pequenos_grupos.count()
    @property
    def meta_ctm_participantes(self):
        meta_pg_unitario = self.area.meta_vigente.meta_ctm_participantes_pg if self.area and self.area.meta_vigente else 0
        return meta_pg_unitario * self.pequenos_grupos.count()
    @property
    def meta_encontro_deus_participantes(self):
        meta_pg_unitario = self.area.meta_vigente.meta_encontro_deus_participantes_pg if self.area and self.area.meta_vigente else 0
        return meta_pg_unitario * self.pequenos_grupos.count()
    @property
    def meta_batizados_aclamados(self):
        meta_pg_unitario = self.area.meta_vigente.meta_batizados_aclamados_pg if self.area and self.area.meta_vigente else 0
        return meta_pg_unitario * self.pequenos_grupos.count()
    @property
    def meta_multiplicacoes_pg(self):
        meta_pg_unitario = self.area.meta_vigente.meta_multiplicacoes_pg_pg if self.area and self.area.meta_vigente else 0
        return meta_pg_unitario * self.pequenos_grupos.count()

    @property
    def membros_do_setor_completos(self):
        membros = set()
        membros.update(self.supervisores)
        for pg in self.pequenos_grupos.all():
            membros.update(pg.membros_completos)
        return list(membros)

    @property
    def num_facilitadores_treinamento_atuais_agregado(self):
        membros_setor = set(self.membros_do_setor_completos)
        count = sum(1 for membro in membros_setor if membro.status_treinamento_pg == 'Facilitador em Treinamento')
        return count

    @property
    def num_anfitrioes_treinamento_atuais_agregado(self):
        membros_setor = set(self.membros_do_setor_completos)
        count = sum(1 for membro in membros_setor if membro.status_treinamento_pg == 'Anfitrião em Treinamento')
        return count

    @property
    def num_ctm_participantes_atuais_agregado(self):
        membros_setor = set(self.membros_do_setor_completos)
        count = sum(1 for membro in membros_setor if membro.presente_ctm_ultimos_30d)
        return count

    @property
    def num_encontro_deus_participantes_atuais_agregado(self):
        membros_setor = set(self.membros_do_setor_completos)
        count = sum(1 for membro in membros_setor if membro.participou_encontro_deus)
        return count

    @property
    def num_batizados_aclamados_atuais_agregado(self):
        membros_setor = set(self.membros_do_setor_completos)
        count = sum(1 for membro in membros_setor if membro.batizado_aclamado)
        return count

    @property
    def num_multiplicacoes_pg_atuais_agregado(self):
        if not self.area.meta_vigente:
            return 0
        
        data_inicio_meta = self.area.meta_vigente.data_inicio
        
        return self.pequenos_grupos.filter(PequenoGrupo.data_multiplicacao >= data_inicio_meta).count()

    @property
    def num_dizimistas_atuais_agregado(self):
        membros_setor = set(self.membros_do_setor_completos)
        count = sum(1 for membro in membros_setor if membro.contribuiu_dizimo_ultimos_30d)
        return count
    
    @property
    def num_participantes_totais_agregado(self):
        return len(self.membros_do_setor_completos)

    @property
    def distribuicao_dizimistas_30d(self):
        try:
            membros_do_setor = self.membros_do_setor_completos
            num_dizimistas = sum(1 for membro in membros_do_setor if membro.contribuiu_dizimo_ultimos_30d)
            num_nao_dizimistas = len(membros_do_setor) - num_dizimistas
            return {'dizimistas': num_dizimistas, 'nao_dizimistas': num_nao_dizimistas}
        except Exception as e:
            print(f"ERRO ao calcular distribuição de dizimistas: {e}")
            return {'dizimistas': 0, 'nao_dizimistas': 0}
        
    @property
    def distribuicao_frequencia_ctm(self):
        membros_do_setor = self.membros_do_setor_completos
        frequentes_ctm = sum(1 for membro in membros_do_setor if membro.presente_ctm_ultimos_30d)
        nao_frequentes_ctm = len(membros_do_setor) - frequentes_ctm
        return {'frequentes_ctm': frequentes_ctm, 'nao_frequentes_ctm': nao_frequentes_ctm}
    
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
    data_multiplicacao = db.Column(db.DateTime, default=datetime.utcnow)

    facilitador = db.relationship('Membro', foreign_keys=[facilitador_id], back_populates='pgs_facilitados')
    anfitriao = db.relationship('Membro', foreign_keys=[anfitriao_id], back_populates='pgs_anfitriados')
    participantes = db.relationship('Membro', foreign_keys='Membro.pg_id', back_populates='pg_participante', lazy='dynamic')
    
    @property
    def meta_facilitadores_treinamento(self):
        return self.setor.area.meta_vigente.meta_facilitadores_treinamento_pg if self.setor and self.setor.area and self.setor.area.meta_vigente else 0
    @property
    def meta_anfitrioes_treinamento(self):
        return self.setor.area.meta_vigente.meta_anfitrioes_treinamento_pg if self.setor and self.setor.area and self.setor.area.meta_vigente else 0
    @property
    def meta_ctm_participantes(self):
        return self.setor.area.meta_vigente.meta_ctm_participantes_pg if self.setor and self.setor.area and self.setor.area.meta_vigente else 0
    @property
    def meta_encontro_deus_participantes(self):
        return self.setor.area.meta_vigente.meta_encontro_deus_participantes_pg if self.setor and self.setor.area and self.setor.area.meta_vigente else 0
    @property
    def meta_batizados_aclamados(self):
        return self.setor.area.meta_vigente.meta_batizados_aclamados_pg if self.setor and self.setor.area and self.setor.area.meta_vigente else 0
    @property
    def meta_multiplicacoes_pg(self):
        return self.setor.area.meta_vigente.meta_multiplicacoes_pg_pg if self.setor and self.setor.area and self.setor.area.meta_vigente else 0

    @property
    def num_facilitadores_treinamento_atuais(self):
        from app.membresia.models import Membro
        membros_completos = self.membros_completos
        count = sum(1 for membro in membros_completos if membro.status_treinamento_pg == 'Facilitador em Treinamento')
        
        return count

    @property
    def num_anfitrioes_treinamento_atuais(self):
        from app.membresia.models import Membro
        membros_completos = self.membros_completos
        count = sum(1 for membro in membros_completos if membro.status_treinamento_pg == 'Anfitrião em Treinamento')
        
        return count

    @property
    def num_ctm_participantes_atuais(self):
        membros_completos = self.membros_completos
        count = sum(1 for membro in membros_completos if membro.presente_ctm_ultimos_30d)
        return count

    @property
    def num_encontro_deus_participantes_atuais(self):
        return db.session.query(Membro).filter(Membro.pg_id == self.id, Membro.participou_encontro_deus == True).count()

    @property
    def num_batizados_aclamados_atuais(self):
        return db.session.query(Membro).filter(Membro.pg_id == self.id, Membro.batizado_aclamado == True).count()

    @property
    def membros_completos(self):
        membros = set(p for p in self.participantes.all())
        if self.facilitador:
            membros.add(self.facilitador)
        if self.anfitriao:
            membros.add(self.anfitriao)
        return list(membros)

    @property
    def num_participantes_totais(self):
        return len(self.membros_completos)

    @property
    def num_dizimistas_atuais(self):
        membros_do_pg = self.membros_completos
        return sum(1 for membro in membros_do_pg if membro.contribuiu_dizimo_ultimos_30d)

    @property
    def membros_para_indicadores(self):
        membros = set(p for p in self.participantes.all())
        if self.anfitriao and self.anfitriao.id != self.facilitador.id:
            membros.add(self.anfitriao)
        return list(membros)

    def __repr__(self):
        return f'<PG: {self.nome} | Facilitador: {self.facilitador.nome_completo}>'
    