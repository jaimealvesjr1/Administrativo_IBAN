from app.extensions import db
from datetime import datetime, date, timedelta
from sqlalchemy.orm import relationship
from app.membresia.models import Membro
from sqlalchemy import func
from app.financeiro.models import Contribuicao

class Area(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(80), unique=True, nullable=False)
    coordenador_id = db.Column(db.Integer, db.ForeignKey('membro.id'), nullable=False)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)

    coordenador = db.relationship('Membro', back_populates='areas_coordenadas', foreign_keys=[coordenador_id])
    setores = db.relationship('Setor', backref='area', lazy='dynamic', cascade='all, delete-orphan')

    meta_facilitadores_treinamento = db.Column(db.Integer, default=0)
    meta_anfitrioes_treinamento = db.Column(db.Integer, default=0)
    meta_ctm_participantes = db.Column(db.Integer, default=0)
    meta_encontro_deus_participantes = db.Column(db.Integer, default=0)
    meta_batizados_aclamados = db.Column(db.Integer, default=0)
    meta_multiplicacoes_pg = db.Column(db.Integer, default=0)

    @property
    def membros_da_area_completos(self):
        membros = set()
        if self.coordenador:
            membros.add(self.coordenador)
        for setor in self.setores.all():
            membros.update(setor.membros_do_setor_completos)
        return list(membros)

    @property
    def num_facilitadores_treinamento_atuais_agregado(self):
        count = sum(setor.num_facilitadores_treinamento_atuais_agregado for setor in self.setores.all())
        if self.coordenador and self.coordenador.status_treinamento_pg == 'Facilitador em Treinamento':
            count += 1
        return count

    @property
    def num_anfitrioes_treinamento_atuais_agregado(self):
        count = sum(setor.num_anfitrioes_treinamento_atuais_agregado for setor in self.setores.all())
        if self.coordenador and self.coordenador.status_treinamento_pg == 'Anfitrião em Treinamento':
            count += 1
        return count

    @property
    def num_ctm_participantes_atuais_agregado(self):
        count = sum(setor.num_ctm_participantes_atuais_agregado for setor in self.setores.all())
        if self.coordenador and self.coordenador.participou_ctm:
            count += 1
        return count

    @property
    def num_encontro_deus_participantes_atuais_agregado(self):
        return sum(setor.num_encontro_deus_participantes_atuais_agregado for setor in self.setores.all())

    @property
    def num_batizados_aclamados_atuais_agregado(self):
        return sum(setor.num_batizados_aclamados_atuais_agregado for setor in self.setores.all())

    @property
    def num_multiplicacoes_pg_atuais_agregado(self):
        return sum(setor.num_multiplicacoes_pg_atuais_agregado for setor in self.setores.all())
    
    @property
    def num_participantes_totais_agregado(self):
        total_de_setores = sum(setor.num_participantes_totais_agregado for setor in self.setores.all())
        
        if self.coordenador:
            return total_de_setores + 1
            
        return total_de_setores

    @property
    def num_dizimistas_atuais_agregado(self):
        num_dizimistas_setores = sum(setor.num_dizimistas_atuais_agregado for setor in self.setores.all())
        if self.coordenador and self.coordenador.contribuiu_dizimo_ultimos_30d:
            return num_dizimistas_setores + 1
        return num_dizimistas_setores

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
    supervisor_id = db.Column(db.Integer, db.ForeignKey('membro.id'), nullable=False)
    area_id = db.Column(db.Integer, db.ForeignKey('area.id'), nullable=False)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)

    supervisor = db.relationship('Membro', back_populates='setores_supervisionados', foreign_keys=[supervisor_id])
    pequenos_grupos = db.relationship('PequenoGrupo', backref='setor', lazy='dynamic', cascade='all, delete-orphan')

    meta_facilitadores_treinamento = db.Column(db.Integer, default=0)
    meta_anfitrioes_treinamento = db.Column(db.Integer, default=0)
    meta_ctm_participantes = db.Column(db.Integer, default=0)
    meta_encontro_deus_participantes = db.Column(db.Integer, default=0)
    meta_batizados_aclamados = db.Column(db.Integer, default=0)
    meta_multiplicacoes_pg = db.Column(db.Integer, default=0)

    @property
    def membros_do_setor_completos(self):
        membros = set()
        if self.supervisor:
            membros.add(self.supervisor)
        for pg in self.pequenos_grupos.all():
            membros.update(pg.membros_completos)
        return list(membros)


    @property
    def num_facilitadores_treinamento_atuais_agregado(self):
        count = sum(pg.num_facilitadores_treinamento_atuais for pg in self.pequenos_grupos.all())
        if self.supervisor and self.supervisor.status_treinamento_pg == 'Facilitador em Treinamento':
            count += 1
        return count

    @property
    def num_anfitrioes_treinamento_atuais_agregado(self):
        count = sum(pg.num_anfitrioes_treinamento_atuais for pg in self.pequenos_grupos.all())
        if self.supervisor and self.supervisor.status_treinamento_pg == 'Anfitrião em Treinamento':
            count += 1
        return count

    @property
    def num_ctm_participantes_atuais_agregado(self):
        count = sum(pg.num_ctm_participantes_atuais for pg in self.pequenos_grupos.all())
        if self.supervisor and self.supervisor.participou_ctm:
            count += 1
        return count

    @property
    def num_encontro_deus_participantes_atuais_agregado(self):
        return sum(pg.num_encontro_deus_participantes_atuais for pg in self.pequenos_grupos.all())

    @property
    def num_batizados_aclamados_atuais_agregado(self):
        return sum(pg.num_batizados_aclamados_atuais for pg in self.pequenos_grupos.all())

    @property
    def num_multiplicacoes_pg_atuais_agregado(self):
        return self.pequenos_grupos.count()

    @property
    def num_dizimistas_atuais_agregado(self):
        num_dizimistas_pgs = sum(pg.num_dizimistas_atuais for pg in self.pequenos_grupos.all())
        if self.supervisor and self.supervisor.contribuiu_dizimo_ultimos_30d:
            return num_dizimistas_pgs + 1
        return num_dizimistas_pgs
    
    @property
    def num_participantes_totais_agregado(self):
        total_de_pgs = sum(pg.num_participantes_totais for pg in self.pequenos_grupos.all())
        
        if self.supervisor:
            return total_de_pgs + 1
        
        return total_de_pgs

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

    facilitador = db.relationship('Membro', back_populates='pgs_facilitados', foreign_keys=[facilitador_id])
    anfitriao = db.relationship('Membro', back_populates='pgs_anfitriados', foreign_keys=[anfitriao_id])
    participantes = db.relationship('Membro', backref='pg_participante', lazy='dynamic', foreign_keys='Membro.pg_id')

    meta_facilitadores_treinamento = db.Column(db.Integer, default=0)
    meta_anfitrioes_treinamento = db.Column(db.Integer, default=0)
    meta_ctm_participantes = db.Column(db.Integer, default=0)
    meta_encontro_deus_participantes = db.Column(db.Integer, default=0)
    meta_batizados_aclamados = db.Column(db.Integer, default=0)
    meta_multiplicacoes_pg = db.Column(db.Integer, default=0)

    @property
    def num_facilitadores_treinamento_atuais(self):
        return self.participantes.filter_by(status_treinamento_pg='Facilitador em Treinamento').count()

    @property
    def num_anfitrioes_treinamento_atuais(self):
        return self.participantes.filter_by(status_treinamento_pg='Anfitrião em Treinamento').count()

    @property
    def num_ctm_participantes_atuais(self):
        return self.participantes.filter_by(participou_ctm=True).count()

    @property
    def num_encontro_deus_participantes_atuais(self):
        return self.participantes.filter_by(participou_encontro_deus=True).count()

    @property
    def num_batizados_aclamados_atuais(self):
        return self.participantes.filter_by(batizado_aclamado=True).count()

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

    def __repr__(self):
        return f'<PG: {self.nome} | Facilitador: {self.facilitador.nome_completo}>'
    