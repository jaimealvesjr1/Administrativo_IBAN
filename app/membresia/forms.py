from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import StringField, SelectField, SubmitField, DateField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional, ValidationError
from config import Config
from datetime import date

class MembroForm(FlaskForm):
    nome_completo = StringField('Nome Completo', validators=[DataRequired(), Length(max=100)])
    data_nascimento = DateField('Data de Nascimento', format='%Y-%m-%d', validators=[DataRequired()])
    data_recepcao = DateField('Data de Recepção', format='%Y-%m-%d', validators=[Optional()]) # Tornando opcional novamente para flexibilidade
    tipo_recepcao = SelectField('Tipo de Recepção', validators=[DataRequired()],
                                 choices=[
                                     ('', 'Selecione...'),
                                     ('Aclamação', 'Aclamação'),
                                     ('Batismo', 'Batismo'),
                                     ('Outro', 'Outro')
                                 ])
    obs_recepcao = TextAreaField('Observações de Membresia', validators=[Length(max=500), Optional()], render_kw={'rows': 2}) # Adicionada validação de tamanho e opcionalidade

    status = SelectField('Status', validators=[DataRequired()])
    campus = SelectField('Campus', validators=[DataRequired()])
    foto_perfil = FileField('Foto de Perfil', validators=[
        FileAllowed(['jpg', 'png', 'jpeg'], 'Apenas imagens JPG, PNG e JPEG são permitidas!'),
        Optional()
    ])

    submit = SubmitField('Salvar')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.status.choices = [('', 'Selecione...')] + [(s, s) for s in Config.STATUS.keys()]
        self.campus.choices = [('', 'Selecione...')] + [(c, c) for c in Config.CAMPUS.keys()]

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
