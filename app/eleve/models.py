from app.extensions import db
from datetime import datetime
from app.membresia.models import Membro

# Subcategorias da Roda da Vida (baseado nos requisitos do documento e template)
RODA_DA_VIDA_SUBCATEGORIAS = [
    'Saúde', 'Família', 'Finanças',            # Pessoal
    'Santidade', 'Tempo de Leitura', 'Tempo de Oração', # Espiritual
    'Culto', 'Liderança', 'Célula',          # Ministerial
    'Carreira', 'Aperfeiçoamento', 'Sonho' # Crescimento
]

class PilulaDiaria(db.Model):
    """Representa o conteúdo semanal/diário de uma Pílula."""
    __tablename__ = 'eleve_pilulas_diarias'
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(100), nullable=False)
    
    data_publicacao = db.Column(db.Date, nullable=False) 
    
    subcategoria_rv = db.Column(db.String(50), nullable=False)
    link_video = db.Column(db.String(255))
    descricao_tarefa = db.Column(db.Text)
    pontos_base = db.Column(db.Integer, default=0)

    questoes_quiz = db.relationship('QuizQuestion', backref='pilula', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<PilulaDiaria {self.titulo} - {self.data_publicacao}>"

class RegistroPresenca(db.Model):
    """Armazena o registro de participação semanal/diária que gera Pontos Base (PG)."""
    __tablename__ = 'eleve_registro_presenca'
    id = db.Column(db.Integer, primary_key=True)
    membro_id = db.Column(db.Integer, db.ForeignKey('membro.id'), nullable=False)
    data = db.Column(db.Date, nullable=False, default=datetime.now().date)
    tipo = db.Column(db.String(50), nullable=False) # 'Pilula', 'Culto', 'PG', 'Servico', 'Encontro'
    pontuacao_ganha = db.Column(db.Integer, nullable=False) # Pontuação Base efetivamente ganha
    pilula_id = db.Column(db.Integer, db.ForeignKey('eleve_pilulas_diarias.id'), nullable=True)

    membro = db.relationship('Membro', backref=db.backref('presencas_eleve', lazy='dynamic'))
    pilula = db.relationship('PilulaDiaria', backref=db.backref('registros_presenca', lazy='dynamic'))

    __table_args__ = (
        db.UniqueConstraint('membro_id', 'data', 'tipo', name='uq_membro_data_tipo_eleve'),
    )

class IndiceProgresso(db.Model):
    """Armazena o Progresso (IP) na Roda da Vida (RV), de 0 a 100 por subcategoria."""
    __tablename__ = 'eleve_indices_progresso'
    id = db.Column(db.Integer, primary_key=True)
    membro_id = db.Column(db.Integer, db.ForeignKey('membro.id'), nullable=False)
    subcategoria_rv = db.Column(db.String(50), nullable=False, unique=True) # Nome da subcategoria
    indice = db.Column(db.Integer, default=0) # Valor de 0 a 100
    ano = db.Column(db.Integer, default=datetime.now().year)

    membro = db.relationship('Membro', backref=db.backref('indices_progresso', lazy='dynamic'))

class PontuacaoAnual(db.Model):
    """Armazena as métricas para o Ranking Anual (PJ, PCr, Slot SC)."""
    __tablename__ = 'eleve_pontuacao_anual'
    id = db.Column(db.Integer, primary_key=True)
    membro_id = db.Column(db.Integer, db.ForeignKey('membro.id'), nullable=False)
    ano = db.Column(db.Integer, default=datetime.now().year, nullable=False)
    pj_total = db.Column(db.Integer, default=0)         # Pontos de Jornada
    pcr_max = db.Column(db.Integer, default=0)          # PCr Máximo em um mês
    num_classificacoes = db.Column(db.Integer, default=0)# Nº de vezes no Top 20%
    pcr_acumulado = db.Column(db.Integer, default=0)    # PCr Acumulado nos meses de classificação
    slot_classificacao = db.Column(db.Boolean, default=False) # Slot Único (SC)

    membro = db.relationship('Membro', backref=db.backref('pontuacao_anual', lazy='dynamic'))

    __table_args__ = (
        db.UniqueConstraint('membro_id', 'ano', name='uq_membro_ano_eleve'),
    )

class RegistroMensal(db.Model):
    """Guarda a pontuação final (PG) de um membro em um Setor em um dado mês/ano, para fins de classificação."""
    __tablename__ = 'eleve_registro_mensal'
    id = db.Column(db.Integer, primary_key=True)
    membro_id = db.Column(db.Integer, db.ForeignKey('membro.id'), nullable=False)
    setor_id = db.Column(db.Integer, db.ForeignKey('setor.id'), nullable=False) # Assumindo um modelo Setor em app/grupos/models.py
    mes = db.Column(db.Integer, nullable=False)
    ano = db.Column(db.Integer, nullable=False)
    pontos_finais_pg = db.Column(db.Integer, default=0) # Pontos Base x Multiplicador Fidelidade
    posicao_no_setor = db.Column(db.Integer, nullable=True)
    classificado_top_20 = db.Column(db.Boolean, default=False)

    membro = db.relationship('Membro', backref=db.backref('registros_mensais', lazy='dynamic'))
    # setor = db.relationship('Setor', backref=db.backref('registros_mensais', lazy='dynamic')) # Necessita do Setor model

    __table_args__ = (
        db.UniqueConstraint('membro_id', 'mes', 'ano', name='uq_membro_mes_ano_eleve'),
    )

class QuizQuestion(db.Model):
    """Armazena uma única pergunta de um Quiz de Pílula."""
    __tablename__ = 'eleve_quiz_questoes'
    id = db.Column(db.Integer, primary_key=True)
    pilula_id = db.Column(db.Integer, db.ForeignKey('eleve_pilulas_diarias.id'), nullable=False)
    texto = db.Column(db.Text, nullable=False)
    
    opcoes = db.relationship('QuizOption', backref='questao', lazy='dynamic', cascade='all, delete-orphan')

class QuizOption(db.Model):
    """Armazena as opções de resposta de múltipla escolha para uma pergunta."""
    __tablename__ = 'eleve_quiz_opcoes'
    id = db.Column(db.Integer, primary_key=True)
    questao_id = db.Column(db.Integer, db.ForeignKey('eleve_quiz_questoes.id'), nullable=False)
    texto = db.Column(db.String(255), nullable=False)
    correta = db.Column(db.Boolean, default=False) # Apenas uma deve ser True por Questão