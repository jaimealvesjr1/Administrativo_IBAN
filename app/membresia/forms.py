from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField, DateField
from wtforms.validators import DataRequired, Length
from config import Config

class MembroForm(FlaskForm):
    nome_completo = StringField('Nome Completo', validators=[DataRequired()])
    data_nascimento = DateField('Data de Nascimento', format='%Y-%m-%d', validators=[DataRequired()])
    data_recepcao = DateField('Data de Recepção', format='%Y-%m-%d', validators=[DataRequired()])
    status = SelectField('Status', choices=[(s, s) for s in Config.STATUS.keys()])
    campus = SelectField('Campus', choices=[(c, c) for c in Config.CAMPUS.keys()])
    submit = SubmitField('Salvar')

class CadastrarNaoMembroForm(FlaskForm):
    nome_completo = StringField('Nome Completo', validators=[DataRequired(), Length(min=3, max=100)])
    data_nascimento = DateField('Data de Nascimento', format='%Y-%m-%d', validators=[DataRequired()])
    campus = SelectField('Campus', validators=[DataRequired()])
    submit = SubmitField('Cadastrar Pessoa')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from config import Config
        self.campus.choices = [(c, c) for c in Config.CAMPUS.keys()]
