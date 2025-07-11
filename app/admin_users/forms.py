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

class UserPermissionsForm(FlaskForm):
    permissions = SelectMultipleField('Permissões',
                                      coerce=str,
                                      option_widget=widgets.CheckboxInput(),
                                      widget=MultiCheckboxWidget())
    submit = SubmitField('Atualizar Permissões')

class AdminResetPasswordForm(FlaskForm):
    new_password = PasswordField('Nova Senha', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField(
        'Confirmar Nova Senha', validators=[DataRequired(), EqualTo('new_password')])
    submit = SubmitField('Redefinir Senha')

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
