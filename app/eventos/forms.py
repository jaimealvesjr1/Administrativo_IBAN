from flask_wtf import FlaskForm
from wtforms import StringField, DateField, SubmitField, SelectMultipleField, SelectField, TextAreaField, HiddenField
from wtforms.validators import DataRequired, Length, ValidationError
from datetime import date
from app.eventos.models import Evento
from app.membresia.models import Membro
from app.grupos.models import Area, Setor, PequenoGrupo

class EventoForm(FlaskForm):
    nome = StringField('Nome do Evento', validators=[DataRequired(), Length(min=2, max=150)])
    tipo_evento = SelectField('Tipo de Evento', validators=[DataRequired()],
                              choices=[('Recepção', 'Recepção'), ('Encontro com Deus', 'Encontro com Deus')])
    data_evento = DateField('Data do Evento', format='%Y-%m-%d', validators=[DataRequired()])
    observacoes = TextAreaField('Observações', validators=[Length(max=500)])
    submit = SubmitField('Salvar Evento')

    def validate_data_evento(self, field):
        if field.data < date.today():
            raise ValidationError('A data do evento não pode ser no passado.')

class InscricaoEventoForm(FlaskForm):
    membro_id = HiddenField('ID do Membro', validators=[DataRequired()])
    presente = SelectField('Status', validators=[DataRequired()],
                           choices=[('false', 'Faltou'), ('true', 'Presente')])
    status_conclusao = SelectField('Conclusão', validators=[DataRequired()],
                                   choices=[('Em Andamento', 'Em Andamento'),
                                            ('Concluiu', 'Concluiu'),
                                            ('Reprovado', 'Reprovado')])
    observacao_admin = TextAreaField('Observações do Administrador', validators=[Length(max=500)])
    submit = SubmitField('Salvar Inscrição')

class InscricaoMembrosForm(FlaskForm):
    membros = SelectMultipleField('Membros', coerce=int)
    submit = SubmitField('Inscrever Selecionados')

    def __init__(self, *args, **kwargs):
        super(InscricaoMembrosForm, self).__init__(*args, **kwargs)
        self.membros.choices = [(m.id, m.nome_completo) for m in Membro.query.order_by(Membro.nome_completo).all()]

class ConclusaoRecepcaoForm(FlaskForm):
    tipo_recepcao = SelectField('Tipo de Recepção', validators=[DataRequired()],
                                 choices=[('Batismo', 'Batismo'), ('Aclamação', 'Aclamação')])
    obs_membresia = TextAreaField('Observação de Membresia', validators=[DataRequired(), Length(max=500)])
    submit = SubmitField('Concluir e Atualizar Membros')
    