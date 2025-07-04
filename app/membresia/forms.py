from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import StringField, SelectField, SubmitField, DateField, BooleanField
from wtforms.validators import DataRequired, Length, Optional, ValidationError
from config import Config
from datetime import date

class MembroForm(FlaskForm):
    nome_completo = StringField('Nome Completo', validators=[DataRequired(), Length(max=100)])
    data_nascimento = DateField('Data de Nascimento', format='%Y-%m-%d', validators=[DataRequired()])
    data_recepcao = DateField('Data de Recepção', format='%Y-%m-%d', validators=[Optional()])
    status = SelectField('Status', choices=[])
    campus = SelectField('Campus', choices=[])
    foto_perfil = FileField('Foto de Perfil', validators=[
        FileAllowed(['jpg', 'png', 'jpeg'], 'Apenas imagens JPG, PNG e JPEG são permitidas!'),
        Optional()
    ])

    submit = SubmitField('Salvar')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.status.choices = [(s, s) for s in Config.STATUS.keys()]
        self.campus.choices = [(c, c) for c in Config.CAMPUS.keys()]

    def validate_data_nascimento(self, field):
        if field.data and field.data > date.today():
            raise ValidationError('A data de nascimento não pode ser no futuro.')

    def validate_data_recepcao(self, field):
        if field.data and field.data > date.today():
            raise ValidationError('A data de recepção não pode ser no futuro.')


class CadastrarNaoMembroForm(FlaskForm):
    nome_completo = StringField('Nome Completo', validators=[DataRequired(), Length(min=3, max=100)])
    data_nascimento = DateField('Data de Nascimento', format='%Y-%m-%d', validators=[DataRequired()])
    campus = SelectField('Campus', validators=[DataRequired()])

    foto_perfil = FileField('Foto de Perfil', validators=[
        FileAllowed(['jpg', 'png', 'jpeg'], 'Apenas imagens JPG, PNG e JPEG são permitidas!'),
        Optional()
    ])

    submit = SubmitField('Cadastrar Pessoa')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.campus.choices = [(c, c) for c in Config.CAMPUS.keys()]

    def validate_data_nascimento(self, field):
        if field.data and field.data > date.today():
            raise ValidationError('A data de nascimento não pode ser no futuro.')
