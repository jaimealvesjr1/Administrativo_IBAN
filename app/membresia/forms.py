from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import StringField, SelectField, SubmitField, DateField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional, ValidationError
from config import Config
from datetime import date
from .models import Membro

class MembroForm(FlaskForm):
    nome_completo = StringField('Nome Completo', validators=[DataRequired(), Length(max=100)])
    data_nascimento = DateField('Data de Nascimento', format='%Y-%m-%d', validators=[DataRequired()])

    data_recepcao = DateField('Data de Recepção', format='%Y-%m-%d', validators=[DataRequired()])
    tipo_recepcao = SelectField('Tipo de Recepção', validators=[DataRequired()],
                                 choices=[
                                     ('', 'Selecione...'),
                                     ('Aclamação', 'Aclamação'),
                                     ('Batismo', 'Batismo'),
                                 ])
    obs_recepcao = TextAreaField('Observações de Membresia', validators=[Length(max=500), Optional()], render_kw={'rows': 2})

    campus = SelectField('Campus', validators=[DataRequired()])
    foto_perfil = FileField('Foto de Perfil', validators=[
        FileAllowed(['jpg', 'png', 'jpeg'], 'Apenas imagens JPG, PNG e JPEG são permitidas!'),
        Optional()
    ])

    submit = SubmitField('Salvar')

    def __init__(self, *args, membro=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.membro = membro
        self.campus.choices = [(c, c) for c in Config.CAMPUS.keys()]

    def validate_nome_completo(self, nome_completo):
        query = Membro.query.filter_by(nome_completo=nome_completo.data)
        membro = Membro.query.filter_by(nome_completo=nome_completo.data).first()
        if self.membro:
            query = query.filter(Membro.id != self.membro.id)
        if query.first():
            raise ValidationError('Já existe um membro cadastrado com este nome completo.')

    def validate_data_nascimento(self, field):
        if field.data and field.data > date.today():
            raise ValidationError('A data de nascimento não pode ser no futuro.')

    def validate_data_recepcao(self, field):
        if field.data and field.data > date.today():
            raise ValidationError('A data de recepção não pode ser no futuro.')

class CadastrarNaoMembroForm(FlaskForm):
    nome_completo = StringField('Nome Completo', validators=[DataRequired(), Length(min=3, max=100)])
    campus = SelectField('Campus', validators=[DataRequired()])

    foto_perfil = FileField('Foto de Perfil', validators=[
        FileAllowed(['jpg', 'png', 'jpeg'], 'Apenas imagens JPG, PNG e JPEG são permitidas!'),
        Optional()
    ])

    submit = SubmitField('Cadastrar Pessoa')

    def __init__(self, *args, membro=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.membro = membro
        self.campus.choices = [(c, c) for c in Config.CAMPUS.keys()]

    def validate_nome_completo(self, nome_completo):
        query = Membro.query.filter_by(nome_completo=nome_completo.data)
        if self.membro:
            query = query.filter(Membro.id != self.membro.id)
        if query.first():
            raise ValidationError('Já existe uma pessoa com este nome completo.')

    def validate_data_nascimento(self, field):
        if field.data and field.data > date.today():
            raise ValidationError('A data de nascimento não pode ser no futuro.')

class EditarMembroForm(FlaskForm):
    nome_completo = StringField('Nome Completo', validators=[DataRequired(), Length(min=2, max=120)])
    data_nascimento = DateField('Data de Nascimento', format='%Y-%m-%d', validators=[DataRequired()])
    foto_perfil = FileField('Alterar Foto de Perfil')
    campus = SelectField('Campus', choices=[(c, c) for c in Config.CAMPUS], validators=[DataRequired()])
    submit = SubmitField('Salvar Alterações')
    
    def __init__(self, *args, **kwargs):
        super(EditarMembroForm, self).__init__(*args, **kwargs)
        self.obj = kwargs.get('obj', None)
    
    def validate_nome_completo(self, nome_completo):
        membro = Membro.query.filter_by(nome_completo=nome_completo.data).first()
        if membro and (not self.obj or membro.id != self.obj.id):
            raise ValidationError('Já existe um membro com este nome. Por favor, escolha outro.')
