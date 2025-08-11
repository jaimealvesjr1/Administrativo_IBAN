from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField, IntegerField
from wtforms.validators import DataRequired, Length, ValidationError, NumberRange
from app.grupos.models import Area, Setor, PequenoGrupo
from app.membresia.models import Membro
from app.extensions import db

class AreaForm(FlaskForm):
    nome = StringField('Nome da Área', validators=[DataRequired(), Length(min=2, max=80)])
    coordenador = SelectField('Coordenador', coerce=int, validators=[DataRequired()])

    meta_facilitadores_treinamento = IntegerField('Facilitadores em Treinamento', default=0, validators=[NumberRange(min=0)])
    meta_anfitrioes_treinamento = IntegerField('Anfitriões em Treinamento', default=0, validators=[NumberRange(min=0)])
    meta_ctm_participantes = IntegerField('Participantes frequentes no CTM', default=0, validators=[NumberRange(min=0)])
    meta_encontro_deus_participantes = IntegerField('Encontro com Deus', default=0, validators=[NumberRange(min=0)])
    meta_batizados_aclamados = IntegerField('Número de Batismos/Aclamações', default=0, validators=[NumberRange(min=0)])
    meta_multiplicacoes_pg = IntegerField('Multiplicações de PG', default=0, validators=[NumberRange(min=0)])
    submit = SubmitField('Salvar Área')

    def __init__(self, *args, **kwargs):
        super(AreaForm, self).__init__(*args, **kwargs)
        self.coordenador.choices = [(m.id, m.nome_completo) for m in Membro.query.order_by(Membro.nome_completo).all()]
        self.coordenador.choices.insert(0, (0, 'Selecione um coordenador'))

    def validate_nome(self, nome):
        area = Area.query.filter_by(nome=nome.data).first()
        if area and (not self.area or area.id != self.area.id):
            raise ValidationError('Já existe uma Área com este nome. Por favor, escolha outro.')

    def validate_coordenador(self, coordenador):
        if coordenador.data == 0:
            raise ValidationError('Por favor, selecione um Coordenador válido.')


class SetorForm(FlaskForm):
    nome = StringField('Nome do Setor', validators=[DataRequired(), Length(min=2, max=80)])
    supervisor = SelectField('Supervisor', coerce=int, validators=[DataRequired()])
    area = SelectField('Área Pertencente', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Salvar Setor')

    def __init__(self, *args, **kwargs):
        super(SetorForm, self).__init__(*args, **kwargs)
        self.supervisor.choices = [(m.id, m.nome_completo) for m in Membro.query.order_by(Membro.nome_completo).all()]
        self.supervisor.choices.insert(0, (0, 'Selecione um supervisor'))
        self.area.choices = [(a.id, a.nome) for a in Area.query.order_by(Area.nome).all()]
        self.area.choices.insert(0, (0, 'Selecione uma área'))

    def validate_nome(self, nome):
        setor = Setor.query.filter_by(nome=nome.data).first()
        if setor and (not self.setor or setor.id != self.setor.id):
            raise ValidationError('Já existe um Setor com este nome. Por favor, escolha outro.')

    def validate_supervisor(self, supervisor):
        if supervisor.data == 0:
            raise ValidationError('Por favor, selecione um Supervisor válido.')

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
        self.facilitador.choices = [(m.id, m.nome_completo) for m in Membro.query.order_by(Membro.nome_completo).all()]
        self.facilitador.choices.insert(0, (0, 'Selecione um facilitador'))
        self.anfitriao.choices = [(m.id, m.nome_completo) for m in Membro.query.order_by(Membro.nome_completo).all()]
        self.anfitriao.choices.insert(0, (0, 'Selecione um anfitrião'))
        self.setor.choices = [(s.id, s.nome) for s in Setor.query.order_by(Setor.nome).all()]
        self.setor.choices.insert(0, (0, 'Selecione um setor'))

    def validate_nome(self, nome):
        pg = PequenoGrupo.query.filter_by(nome=nome.data).first()
        if pg and (not self.pg or pg.id != self.pg.id):
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

class PequenoGrupoMetasForm(FlaskForm):
    meta_facilitadores_treinamento = IntegerField('Facilitadores em Treinamento', default=0, validators=[NumberRange(min=0)])
    meta_anfitrioes_treinamento = IntegerField('Anfitriões em Treinamento', default=0, validators=[NumberRange(min=0)])
    meta_ctm_participantes = IntegerField('Participantes frequentes no CTM', default=0, validators=[NumberRange(min=0)])
    meta_encontro_deus_participantes = IntegerField('Participantes no Encontro com Deus', default=0, validators=[NumberRange(min=0)])
    meta_batizados_aclamados = IntegerField('Batizados/Aclamados', default=0, validators=[NumberRange(min=0)])
    meta_multiplicacoes_pg = IntegerField('Multiplicações de PGs', default=0, validators=[NumberRange(min=0)])
    submit = SubmitField('Salvar Metas')


class SetorMetasForm(FlaskForm):
    meta_facilitadores_treinamento = IntegerField('Facilitadores em Treinamento', default=0, validators=[NumberRange(min=0)])
    meta_anfitrioes_treinamento = IntegerField('Anfitriões em Treinamento', default=0, validators=[NumberRange(min=0)])
    meta_ctm_participantes = IntegerField('Participantes frequentes no CTM', default=0, validators=[NumberRange(min=0)])
    meta_encontro_deus_participantes = IntegerField('Participantes no Encontro com Deus', default=0, validators=[NumberRange(min=0)])
    meta_batizados_aclamados = IntegerField('Número de Batizados/Aclamados', default=0, validators=[NumberRange(min=0)])
    meta_multiplicacoes_pg = IntegerField('Multiplicações de PGs', default=0, validators=[NumberRange(min=0)])
    submit = SubmitField('Salvar Metas')
