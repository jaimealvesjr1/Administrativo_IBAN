from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, SelectMultipleField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError
from app.auth.models import User
from app.membresia.models import Membro

def coerce_to_int_or_none(value):
    if value == '':
        return None
    return int(value)

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Senha', validators=[DataRequired()])
    submit = SubmitField('Entrar')

class MembroRegistrationForm(FlaskForm):
    membro_id = SelectField('Seu Nome Completo', coerce=coerce_to_int_or_none, validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Senha', validators=[DataRequired()])
    password2 = PasswordField(
        'Repita a Senha', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Criar Acesso')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        membros_sem_acesso = Membro.query.outerjoin(User).filter(User.membro_id == None).order_by(Membro.nome_completo).all()
        
        if not membros_sem_acesso:
            self.membro_id.choices = [('', 'Nenhum membro disponível para registro')]
        else:
            self.membro_id.choices = [('', 'Selecione seu nome na lista')]
            self.membro_id.choices.extend([(m.id, m.nome_completo) for m in membros_sem_acesso])
    
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Email já cadastrado.')

    def validate_membro_id(self, membro_id):
        user = User.query.filter_by(membro_id=membro_id.data).first()
        if user is not None:
            raise ValidationError('Este membro já possui um acesso vinculado.')
