from flask_wtf import FlaskForm
from wtforms import SelectField, SubmitField, DateField, FloatField, TextAreaField, StringField
from wtforms.validators import DataRequired, NumberRange, Optional
from config import Config
from app.membresia.models import Membro

def coerce_to_int_or_none(value):
    if value == '':
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None

class ContribuicaoForm(FlaskForm):
    membro_id = SelectField('Membro', coerce=coerce_to_int_or_none, validators=[DataRequired()])
    tipo = SelectField('Tipo', choices=[(t, t) for t in Config.TIPOS], validators=[DataRequired()])
    valor = FloatField('Valor (R$)', validators=[DataRequired(), NumberRange(min=0.01)])
    data_lanc = DateField('Data', validators=[DataRequired()])
    forma = SelectField('Forma de Contribuição', choices=[(f, f) for f in Config.FORMAS], validators=[DataRequired()])
    observacoes = TextAreaField('Observações', render_kw={'rows': 3})
    submit = SubmitField('Lançar Contribuição')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tipo.choices = [(t, t) for t in Config.TIPOS]
        self.forma.choices = [(f, f) for f in Config.FORMAS]

class ContribuicaoFilterForm(FlaskForm):
    csrf_enabled = False
    
    busca_nome = StringField('Por nome', validators=[Optional()])
    tipo_filtro = SelectField('Por Tipo', validators=[Optional()])
    campus_filtro = SelectField('Por Campus', validators=[Optional()])
    status_filtro = SelectField('Por Status', validators=[Optional()])
    data_inicial = DateField('Data Inicial', format='%Y-%m-%d', validators=[Optional()])
    data_final = DateField('Data Final', format='%Y-%m-%d', validators=[Optional()])
    submit_filter = SubmitField('Filtrar')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tipo_filtro.choices = [('', 'Todos os Tipos')] + [(t, t) for t in Config.TIPOS]
        self.campus_filtro.choices = [('', 'Todos os Campus')] + [(c, c) for c in Config.CAMPUS.keys()]
        self.status_filtro.choices = [('', 'Todos os Status')] + [(s, s) for s in Config.STATUS.keys()]
