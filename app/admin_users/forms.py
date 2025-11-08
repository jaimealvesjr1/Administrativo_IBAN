from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectMultipleField
from wtforms.validators import DataRequired, Email, Optional, Length, EqualTo, ValidationError
from wtforms import widgets
from app.auth.models import User
from markupsafe import Markup

class MultiCheckboxWidget(widgets.ListWidget):
    def __call__(self, field, **kwargs):
        kwargs.setdefault('id', field.id)
        html = [f'<div {widgets.html_params(**kwargs)}>']
        for subfield in field:
            html.append(f'<div class="form-check">'
                        f'<input class="form-check-input" type="checkbox" '
                        f'name="{subfield.name}" value="{subfield.data}" '
                        f'{"checked" if subfield.checked else ""} id="{subfield.id}">'
                        f'<label class="form-check-label" for="{subfield.id}">{subfield.label.text}</label>'
                        f'</div>')
        html.append('</div>')
        return Markup(''.join(html))

class RequestResetPasswordForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Redefinir Senha')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is None:
            raise ValidationError('Não há conta com este email.')

class ResetPasswordForm(FlaskForm):
    password = PasswordField('Nova Senha', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField(
        'Confirmar Nova Senha', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Alterar Senha')

class UserEditForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField(
        'Nova Senha (opcional)',
        validators=[
            Optional(),
            Length(min=8, message="A senha deve ter no mínimo 8 caracteres.")
        ]
    )
    password2 = PasswordField(
        'Repetir Nova Senha',
        validators=[
            EqualTo('password', message="As senhas não coincidem.")
        ]
    )
    permissions = SelectMultipleField(
        'Permissões',
        choices=[
            ('admin', 'Admin'), 
            ('financeiro', 'Financeiro'), 
            ('secretaria', 'Secretaria')
        ], 
        widget=widgets.ListWidget(prefix_label=False), 
        option_widget=widgets.CheckboxInput()
    )
    submit = SubmitField('Salvar')

    def __init__(self, original_email, *args, **kwargs):
        self.request_user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.original_email = original_email

    def validate_email(self, email):
        if email.data != self.original_email:
            user = User.query.filter_by(email=self.email.data).first()
            if user is not None:
                raise ValidationError('Este email já está em uso.')
