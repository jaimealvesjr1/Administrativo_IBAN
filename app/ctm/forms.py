from flask_wtf import FlaskForm
from wtforms import StringField, DateField, IntegerField, SubmitField, SelectField
from wtforms.validators import DataRequired, Optional, NumberRange, ValidationError
from app.membresia.models import Membro
from .models import ClasseCTM, TurmaCTM, AulaModelo, AulaRealizada
from config import Config
from app.grupos.models import Area, Setor, PequenoGrupo

def coerce_to_int_or_none(value):
    if value == '':
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None

class ClasseCTMForm(FlaskForm):
    nome = StringField('Nome da Classe', validators=[DataRequired()])
    supervisor_id = SelectField('Supervisor da Classe', coerce=coerce_to_int_or_none, validators=[DataRequired()])
    num_aulas_ciclo = IntegerField('Número de Aulas no Ciclo', default=4, validators=[DataRequired(), NumberRange(min=1)])
    submit = SubmitField('Salvar Classe')

    def validate_nome(self, field):
        classe = ClasseCTM.query.filter_by(nome=field.data).first()
        if classe and (not self.obj or classe.id != self.obj.id):
            raise ValidationError('Já existe uma classe com este nome. Por favor, escolha um nome diferente.')

    def __init__(self, *args, **kwargs):
        super(ClasseCTMForm, self).__init__(*args, **kwargs)
        self.obj = kwargs.get('obj', None)
        self.supervisor_id.choices = [('', 'Selecione um supervisor')] + \
                                     [(m.id, m.nome_completo) for m in Membro.query.filter_by(ativo=True).order_by(Membro.nome_completo).all()]

class TurmaCTMForm(FlaskForm):
    nome = StringField('Nome da Turma', validators=[DataRequired()])
    classe_id = SelectField('Classe da Turma', coerce=coerce_to_int_or_none, validators=[DataRequired()])
    facilitador_id = SelectField('Facilitador da Turma', coerce=coerce_to_int_or_none, validators=[DataRequired()])
    submit = SubmitField('Salvar Turma')

    def validate_nome(self, field):
        turma = TurmaCTM.query.filter_by(nome=field.data, classe_id=self.classe_id.data).first()
        if turma and (not self.obj or turma.id != self.obj.id):
            raise ValidationError(f'Já existe uma turma com este nome na classe selecionada. Por favor, escolha um nome diferente.')

    def __init__(self, *args, **kwargs):
        super(TurmaCTMForm, self).__init__(*args, **kwargs)
        self.obj = kwargs.get('obj', None)
        self.classe_id.choices = [('', 'Selecione uma classe')] + \
                                 [(c.id, c.nome) for c in ClasseCTM.query.order_by(ClasseCTM.nome).all()]
        self.facilitador_id.choices = [('', 'Selecione um facilitador')] + \
                                     [(m.id, m.nome_completo) for m in Membro.query.filter_by(ativo=True).order_by(Membro.nome_completo).all()]

class AulaModeloForm(FlaskForm):
    tema = StringField('Tema da Aula', validators=[DataRequired()])
    ordem = IntegerField('Número da Aula', validators=[DataRequired(), NumberRange(min=1)])
    classe_id = SelectField('Classe da Aula', coerce=coerce_to_int_or_none, validators=[DataRequired()])
    submit = SubmitField('Cadastrar Aula Modelo')

    def validate_ordem(self, field):
        aula = AulaModelo.query.filter_by(classe_id=self.classe_id.data, ordem=field.data).first()
        if aula and (not self.obj or aula.id != self.obj.id):
            raise ValidationError('Já existe uma aula com este número de ordem para esta classe.')
            
    def __init__(self, *args, **kwargs):
        super(AulaModeloForm, self).__init__(*args, **kwargs)
        self.obj = kwargs.get('obj', None)
        self.classe_id.choices = [('', 'Selecione uma classe')] + \
                                 [(c.id, c.nome) for c in ClasseCTM.query.order_by(ClasseCTM.nome).all()]

class AulaRealizadaForm(FlaskForm):
    data = DateField('Data da Aula', format='%Y-%m-%d', validators=[DataRequired()])
    turma_id = SelectField('Turma', coerce=coerce_to_int_or_none, validators=[DataRequired()])
    aula_modelo_id = SelectField('Aula Referência', coerce=coerce_to_int_or_none, validators=[DataRequired()])
    chave = StringField('Palavra-Chave para Confirmação', validators=[DataRequired()])
    submit = SubmitField('Cadastrar Aula Realizada')

    def __init__(self, *args, **kwargs):
        super(AulaRealizadaForm, self).__init__(*args, **kwargs)
        self.turma_id.choices = [('', 'Selecione a Turma')] + \
                                 [(t.id, f"{t.nome} - {t.classe.nome}") for t in TurmaCTM.query.filter_by(ativa=True).order_by(TurmaCTM.nome).all()]
        self.aula_modelo_id.choices = [('', 'Selecione a Aula Modelo')] + \
                                     [(a.id, f"{a.ordem} - {a.tema} ({a.classe.nome})") for a in AulaModelo.query.order_by(AulaModelo.classe_id, AulaModelo.ordem).all()]

    def validate_data(self, field):
        turma_id = self.turma_id.data
        if turma_id and AulaRealizada.query.filter_by(data=field.data, turma_id=turma_id).first():
            raise ValidationError('Já existe uma aula cadastrada para esta data nesta turma.')

class PresencaForm(FlaskForm):
    membro_id = SelectField('Nome do Aluno', coerce=coerce_to_int_or_none, validators=[DataRequired()])
    palavra_chave_aula = StringField('Palavra-Chave da Aula', validators=[DataRequired()])
    avaliacao = SelectField('Avaliação da Aula (1 a 5 estrelas)', coerce=coerce_to_int_or_none, validators=[Optional()])
    submit = SubmitField('Registrar Presença')

    def __init__(self, *args, **kwargs):
        super(PresencaForm, self).__init__(*args, **kwargs)
        self.membro_id.choices = [('', 'Selecione seu nome')] + \
                                 [(m.id, m.nome_completo) for m in Membro.query.filter_by(ativo=True).order_by(Membro.nome_completo).all()]
        self.avaliacao.choices = [
            ('', 'Selecione a avaliação'),
            (1, '⭐'),
            (2, '⭐⭐'),
            (3, '⭐⭐⭐'),
            (4, '⭐⭐⭐⭐'),
            (5, '⭐⭐⭐⭐⭐')
        ]

class PresencaManualForm(FlaskForm):
    aula_realizada_id = SelectField('Selecione a Aula', coerce=coerce_to_int_or_none, validators=[DataRequired()])
    membro_id = SelectField('Selecione o Membro', coerce=coerce_to_int_or_none, validators=[DataRequired()])
    submit = SubmitField('Adicionar Presença Manual')

    def __init__(self, *args, **kwargs):
        super(PresencaManualForm, self).__init__(*args, **kwargs)
        aulas_disponiveis = AulaRealizada.query.order_by(AulaRealizada.data.desc()).all()
        self.aula_realizada_id.choices = [('', 'Selecione a aula')]
        self.aula_realizada_id.choices.extend([
            (a.id, f"{a.data.strftime('%d/%m/%Y')} - Turma: {a.turma.nome}")
            for a in aulas_disponiveis
        ])
        
        self.membro_id.choices = [('', 'Selecione um membro')] + \
                                 [(m.id, m.nome_completo) for m in Membro.query.filter_by(ativo=True).order_by(Membro.nome_completo).all()]
