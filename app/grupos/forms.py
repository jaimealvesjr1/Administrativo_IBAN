from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField, IntegerField, SelectMultipleField, DateField
from wtforms.validators import DataRequired, Length, ValidationError, NumberRange
from app.grupos.models import Area, Setor, PequenoGrupo
from app.membresia.models import Membro
from app.extensions import db
from datetime import date

class AreaForm(FlaskForm):
    nome = StringField('Nome da Área', validators=[DataRequired(), Length(min=2, max=80)])
    supervisores = SelectMultipleField('Supervisores da Área', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Salvar Área')

    def __init__(self, *args, **kwargs):
        super(AreaForm, self).__init__(*args, **kwargs)
        self.obj = kwargs.get('obj', None)
        self.supervisores.choices = [(m.id, m.nome_completo) for m in Membro.query.order_by(Membro.nome_completo).all()]


    def validate_nome(self, nome):
        area = Area.query.filter_by(nome=nome.data).first()
        if area and (not self.obj or area.id != self.obj.id):
            raise ValidationError('Já existe uma Área com este nome. Por favor, escolha outro.')

class SetorForm(FlaskForm):
    nome = StringField('Nome do Setor', validators=[DataRequired(), Length(min=2, max=80)])
    supervisores = SelectMultipleField('Supervisores do Setor', coerce=int, validators=[DataRequired()])
    area = SelectField('Área Pertencente', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Salvar Setor')

    def __init__(self, *args, **kwargs):
        super(SetorForm, self).__init__(*args, **kwargs)
        self.obj = kwargs.get('obj', None)
        self.supervisores.choices = [(m.id, m.nome_completo) for m in Membro.query.order_by(Membro.nome_completo).all()]
        self.area.choices = [(a.id, a.nome) for a in Area.query.order_by(Area.nome).all()]
        self.area.choices.insert(0, (0, 'Selecione uma área'))

    def validate_nome(self, nome):
        setor = Setor.query.filter_by(nome=nome.data).first()
        if setor and (not self.obj or setor.id != self.obj.id):
            raise ValidationError('Já existe um Setor com este nome. Por favor, escolha outro.')

    def validate_supervisores(self, field):
        if not field.data:
            raise ValidationError('Por favor, selecione pelo menos um Supervisor válido.')

    def validate_area(self, area):
        if area.data == 0:
            raise ValidationError('Por favor, selecione uma Área válida.')


class PequenoGrupoForm(FlaskForm):
    nome = StringField('Nome do PG', validators=[DataRequired(), Length(min=2, max=100)])
    facilitador = SelectField('Facilitador', coerce=int, validators=[DataRequired()])
    anfitriao = SelectField('Anfitrião', coerce=int, validators=[DataRequired()])
    setor = SelectField('Setor', coerce=int, validators=[DataRequired()])
    dia_reuniao = SelectField('Dia da Reunião', validators=[DataRequired()],
                              choices=[('Segunda-feira', 'Segunda-feira'),
                                       ('Terça-feira', 'Terça-feira'),
                                       ('Quarta-feira', 'Quarta-feira'),
                                       ('Quinta-feira', 'Quinta-feira'),
                                       ('Sexta-feira', 'Sexta-feira'),
                                       ('Sábado', 'Sábado')])
    horario_reuniao = StringField('Horário da Reunião (Ex: 19:30)', validators=[DataRequired()])

    submit = SubmitField('Salvar Pequeno Grupo')

    def __init__(self, *args, **kwargs):
        super(PequenoGrupoForm, self).__init__(*args, **kwargs)
        self.obj = kwargs.get('obj', None)
        self.facilitador.choices = [(m.id, m.nome_completo) for m in Membro.query.order_by(Membro.nome_completo).all()]
        self.facilitador.choices.insert(0, (0, 'Selecione um facilitador'))
        self.anfitriao.choices = [(m.id, m.nome_completo) for m in Membro.query.order_by(Membro.nome_completo).all()]
        self.anfitriao.choices.insert(0, (0, 'Selecione um anfitrião'))
        self.setor.choices = [(s.id, s.nome) for s in Setor.query.order_by(Setor.nome).all()]
        self.setor.choices.insert(0, (0, 'Selecione um setor'))

    def validate_nome(self, nome):
        pg = PequenoGrupo.query.filter_by(nome=nome.data).first()
        if pg and (not self.obj or pg.id != self.obj.id):
            raise ValidationError('Já existe um Pequeno Grupo com este nome. Por favor, escolha outro.')

    def validate_facilitador(self, facilitador):
        if facilitador.data == 0:
            raise ValidationError('Por favor, selecione um Facilitador válido.')

    def validate_anfitriao(self, anfitriao):
        if anfitriao.data == 0:
            raise ValidationError('Por favor, selecione um Anfitrião válido.')

    def validate_setor(self, setor):
        if setor.data == 0:
            raise ValidationError('Por favor, selecione um Setor válido.')

class AreaMetasForm(FlaskForm):
    meta_facilitadores_treinamento_pg = IntegerField('Facilitadores em Treinamento por PG', default=0, validators=[NumberRange(min=0)])
    meta_anfitrioes_treinamento_pg = IntegerField('Anfitriões em Treinamento por PG', default=0, validators=[NumberRange(min=0)])
    meta_ctm_participantes_pg = IntegerField('Participantes frequentes no CTM por PG', default=0, validators=[NumberRange(min=0)])
    meta_encontro_deus_participantes_pg = IntegerField('Encontro com Deus por PG', default=0, validators=[NumberRange(min=0)])
    meta_batizados_aclamados_pg = IntegerField('Batizados/Aclamados por PG', default=0, validators=[NumberRange(min=0)])
    meta_multiplicacoes_pg_pg = IntegerField('Multiplicações de PGs por PG', default=0, validators=[NumberRange(min=0)])
    
    data_fim = DateField('Data de Validade da Meta', validators=[DataRequired()])
    submit = SubmitField('Salvar Metas')

    def validate_data_fim(self, field):
        if field.data <= date.today():
            raise ValidationError('A data de validade deve ser no futuro.')
