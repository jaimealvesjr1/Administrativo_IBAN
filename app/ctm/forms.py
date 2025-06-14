from flask_wtf import FlaskForm
from wtforms import StringField, DateField, IntegerField, SubmitField, SelectField
from wtforms.validators import DataRequired, Optional, NumberRange, ValidationError
from app.membresia.models import Membro
from .models import Aula
from config import Config

def coerce_to_int_or_none(value):
    if value == '':
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None

class PresencaForm(FlaskForm):
    membro_id = SelectField('Nome do Aluno', coerce=coerce_to_int_or_none, validators=[DataRequired()])
        
    avaliacao = SelectField('Avaliação da Aula (1 a 5 estrelas)', coerce=coerce_to_int_or_none, validators=[DataRequired()])
    palavra_chave_aula = StringField('Palavra-Chave da Aula', validators=[DataRequired()])
    
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
    aula_id = SelectField('Selecione a Aula', coerce=coerce_to_int_or_none, validators=[DataRequired()])
    membro_id = SelectField('Selecione o Membro', coerce=coerce_to_int_or_none, validators=[DataRequired()])
    submit = SubmitField('Adicionar Presença Manual')

    def __init__(self, *args, **kwargs):
        super(PresencaManualForm, self).__init__(*args, **kwargs)
        aulas_disponiveis = Aula.query.order_by(Aula.data.desc()).all()
        self.aula_id.choices = [('', 'Selecione a aula')]
        self.aula_id.choices.extend([
            (a.id, f"{a.data.strftime('%d/%m/%Y')} - {a.tema}")
            for a in aulas_disponiveis
        ])
        
        self.membro_id.choices = [('', 'Selecione um membro')] + \
                                 [(m.id, m.nome_completo) for m in Membro.query.filter_by(ativo=True).order_by(Membro.nome_completo).all()]

class AulaForm(FlaskForm):
    data = DateField('Data da Aula', format='%Y-%m-%d', validators=[DataRequired()])
    tema = StringField('Tema da Aula', validators=[DataRequired()])
    chave = StringField('Palavra-Chave para Confirmação', validators=[DataRequired()])
    submit = SubmitField('Cadastrar Aula')

    def validate_data(self, field):
        from .models import Aula
        if Aula.query.filter_by(data=field.data).first():
            raise ValidationError('Já existe uma aula cadastrada para esta data.')
