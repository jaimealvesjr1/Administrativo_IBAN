from app.extensions import db
from datetime import datetime
from app.jornada.models import registrar_evento_jornada

aluno_turma = db.Table('aluno_turma',
    db.Column('membro_id', db.Integer, db.ForeignKey('membro.id'), primary_key=True),
    db.Column('turma_id', db.Integer, db.ForeignKey('turma_ctm.id'), primary_key=True)
)

class ConclusaoCTM(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    membro_id = db.Column(db.Integer, db.ForeignKey('membro.id'), nullable=False)
    turma_id = db.Column(db.Integer, db.ForeignKey('turma_ctm.id'), nullable=False)
    status_conclusao = db.Column(db.String(20), nullable=False)

    __table_args__ = (
        db.UniqueConstraint('membro_id', 'turma_id', name='_membro_turma_uc'),
    )

    membro = db.relationship('Membro', backref=db.backref('conclusoes_ctm', lazy=True))
    turma = db.relationship('TurmaCTM', backref=db.backref('conclusoes_alunos', lazy=True))

    def __repr__(self):
        return f'<ConclusaoCTM {self.status_conclusao} - Membro: {self.membro.nome_completo}>'

class ClasseCTM(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), nullable=False, unique=True)
    supervisor_id = db.Column(db.Integer, db.ForeignKey('membro.id'), nullable=True)

    supervisor = db.relationship('Membro', backref='classes_supervisionadas', lazy=True)
    turmas = db.relationship('TurmaCTM', backref='classe', lazy=True)
    aulas_modelo = db.relationship('AulaModelo', backref='classe', lazy=True)

class TurmaCTM(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), nullable=False)
    classe_id = db.Column(db.Integer, db.ForeignKey('classe_ctm.id'), nullable=False)
    facilitador_id = db.Column(db.Integer, db.ForeignKey('membro.id'), nullable=True)
    ativa = db.Column(db.Boolean, default=True)
    num_aulas_ciclo = db.Column(db.Integer, default=4)

    facilitador = db.relationship('Membro', backref='turmas_facilitadas_ctm', lazy=True)
    alunos = db.relationship('Membro', secondary=aluno_turma, lazy='subquery',
                             backref=db.backref('turmas_ctm', lazy=True))
    aulas_realizadas = db.relationship('AulaRealizada', backref='turma', lazy=True)

    @property
    def data_inicio(self):
        primeira_aula = AulaRealizada.query.filter_by(turma_id=self.id).order_by(AulaRealizada.data.asc()).first()
        return primeira_aula.data if primeira_aula else None
    
    @property
    def data_termino(self):
        ultima_aula = AulaRealizada.query.filter_by(turma_id=self.id).order_by(AulaRealizada.data.desc()).first()
        return ultima_aula.data if ultima_aula else None

class AulaModelo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tema = db.Column(db.String(100), nullable=False)
    ordem = db.Column(db.Integer, nullable=False)
    classe_id = db.Column(db.Integer, db.ForeignKey('classe_ctm.id'), nullable=False)
    
    def __repr__(self):
        return f"<AulaModelo {self.ordem} - {self.tema}>"

class AulaRealizada(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.Date, nullable=False)
    chave = db.Column(db.String(10), nullable=False)
    aula_modelo_id = db.Column(db.Integer, db.ForeignKey('aula_modelo.id'), nullable=False)
    turma_id = db.Column(db.Integer, db.ForeignKey('turma_ctm.id'), nullable=False)
    
    aula_modelo = db.relationship('AulaModelo', backref='realizadas', lazy=True)
    
    __table_args__ = (
        db.UniqueConstraint('data', 'turma_id', name='_data_turma_uc'),
    )
    
    presencas_associadas = db.relationship('Presenca', backref='aula_realizada', lazy=True)

    def __repr__(self):
        return f"<AulaRealizada {self.data} - Turma {self.turma.nome if self.turma else 'N/A'}>"

class Presenca(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    membro_id = db.Column(db.Integer, db.ForeignKey('membro.id'), nullable=False)
    aula_realizada_id = db.Column(db.Integer, db.ForeignKey('aula_realizada.id'), nullable=False)
    avaliacao = db.Column(db.Integer)

    __table_args__ = (
        db.UniqueConstraint('membro_id', 'aula_realizada_id', name='_membro_aula_realizada_uc'),
    )

    def __repr__(self):
        return f"<Presenca {self.id} - Membro: {self.membro.nome_completo if self.membro else 'N/A'} - Data: {self.aula_realizada.data if self.aula_realizada else 'N/A'}>"
    
    def registrar_evento_jornada(self):
        from app.membresia.models import Membro
        membro = Membro.query.get(self.membro_id)
        aula_realizada = AulaRealizada.query.get(self.aula_realizada_id)
        if membro and aula_realizada:
            tema_aula = aula_realizada.aula_modelo.tema if aula_realizada.aula_modelo else 'Tema não definido'
            descricao = f'Participou da aula {tema_aula}.'
            membro.registrar_evento_jornada(descricao, 'Presenca')
