from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField, IntegerField, SelectMultipleField, DateField, Form, FieldList, FormField
from wtforms.validators import DataRequired, Length, ValidationError, NumberRange
from app.grupos.models import Area, Setor, PequenoGrupo
from app.membresia.models import Membro
from app.extensions import db
from flask_login import current_user
from datetime import date

class AreaForm(FlaskForm):
    nome = StringField('Nome da Área', validators=[DataRequired(), Length(min=2, max=80)])
    supervisores = SelectMultipleField('Supervisores da Área', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Salvar Área')

    def __init__(self, *args, **kwargs):
        super(AreaForm, self).__init__(*args, **kwargs)
        self.obj = kwargs.get('obj', None)
        if self.obj and self.obj.supervisores:
            self.supervisores.choices = [(s.id, s.nome_completo) for s in self.obj.supervisores]

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
    class Meta:
        csrf = False

    nome = StringField('Nome do PG', validators=[DataRequired(), Length(min=2, max=100)])
    facilitador = SelectField('Facilitador', coerce=int, validators=[DataRequired()])
    anfitriao = SelectField('Anfitrião', coerce=int, validators=[DataRequired()])
    setor = SelectField('Setor', coerce=int)
    dia_reuniao = SelectField('Dia da Reunião', validators=[DataRequired()],
                              choices=[('Segunda-feira', 'Segunda-feira'),
                                       ('Terça-feira', 'Terça-feira'),
                                       ('Quarta-feira', 'Quarta-feira'),
                                       ('Quinta-feira', 'Quinta-feira'),
                                       ('Sexta-feira', 'Sexta-feira'),
                                       ('Sábado', 'Sábado')])
    horario_reuniao = StringField('Horário (Ex: 19:30)', validators=[DataRequired()])

    submit = SubmitField('Salvar Pequeno Grupo')

    def __init__(self, *args, **kwargs):
        self.pg = kwargs.pop('pg', None)
        self.current_user = kwargs.pop('current_user', current_user)
        self.is_admin = kwargs.pop('is_admin', False)
        self.is_area_supervisor = kwargs.pop('is_area_supervisor', False)
        self.is_sector_supervisor = kwargs.pop('is_sector_supervisor', False)
        self.is_facilitator = kwargs.pop('is_facilitator', False)
        self.pg_antigo_id = kwargs.pop('pg_antigo_id', None) 

        super(PequenoGrupoForm, self).__init__(*args, **kwargs)

        membros_ativos = Membro.query.filter_by(ativo=True).order_by(Membro.nome_completo).all()
        membros_choices = [(m.id, m.nome_completo) for m in membros_ativos]
        membros_choices.insert(0, (0, 'Selecione um membro'))
        
        self.facilitador.choices = membros_choices
        self.anfitriao.choices = membros_choices

        setores_ativos = Setor.query.order_by(Setor.nome).all()
        setor_choices = [(s.id, s.nome) for s in setores_ativos]
        setor_choices.insert(0, (0, 'Selecione um setor'))

        self.setor.choices = setor_choices

        if kwargs.get('obj', None):
            obj = kwargs['obj']
            if hasattr(obj, 'facilitador_id') and obj.facilitador_id:
                self.facilitador.data = obj.facilitador_id
            if hasattr(obj, 'anfitriao_id') and obj.anfitriao_id:
                self.anfitriao.data = obj.anfitriao_id
            if hasattr(obj, 'setor_id') and obj.setor_id:
                self.setor.data = obj.setor_id

        if self.pg: 
            can_edit_lideranca = self.is_admin or self.is_area_supervisor or self.is_sector_supervisor
            if not can_edit_lideranca:
                self.facilitador.render_kw = {'disabled': True}
                self.anfitriao.render_kw = {'disabled': True}

            can_edit_setor = self.is_admin or self.is_area_supervisor
            if not can_edit_setor:
                self.setor.render_kw = {'disabled': True}

            can_edit_dia_horario = self.is_admin or self.is_area_supervisor or self.is_sector_supervisor or self.is_facilitator
            if not can_edit_dia_horario:
                self.dia_reuniao.render_kw = {'disabled': True}
                self.horario_reuniao.render_kw = {'disabled': True}
            
            if not self.pg.ativo and not self.is_admin:
                for field_name in ['nome', 'facilitador', 'anfitriao', 'setor', 'dia_reuniao', 'horario_reuniao']:
                    field = getattr(self, field_name)
                    field.render_kw = {'disabled': True}

    def validate_nome(self, nome):
        if not nome.data:
            return
        pg = PequenoGrupo.query.filter_by(nome=nome.data).first()

        if pg:
            if self.pg and pg.id == self.pg.id:
                pass
            elif self.pg_antigo_id and pg.id == self.pg_antigo_id:
                pass
            elif pg.ativo:
                raise ValidationError('Já existe um Pequeno Grupo ATIVO com este nome. Por favor, escolha outro.')
            
        if self.pg:
            if self.pg.nome != nome.data:
                if not current_user.has_permission('admin'):
                    raise ValidationError('O nome do Pequeno Grupo não pode ser alterado após a criação.')
                            
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
    
    data_inicio = DateField('Data de Início', validators=[DataRequired()])
    data_fim = DateField('Data Limite', validators=[DataRequired()])
    submit = SubmitField('Salvar Metas')

    def validate_data_fim(self, field):
        if field.data <= self.data_inicio.data:
            raise ValidationError('A data limite deve ser posterior à data de início.')

    def validate_data_inicio(self, field):
        if field.data >= self.data_fim.data:
            raise ValidationError('A data de início deve ser anterior à data de validade.')

class MultiplicacaoForm(FlaskForm):
    pg1 = FormField(PequenoGrupoForm)
    pg2 = FormField(PequenoGrupoForm)
    data_multiplicacao = DateField('Data da Multiplicação', validators=[DataRequired()])
    submit = SubmitField('Multiplicar PG')

    def __init__(self, *args, **kwargs):
        pg_antigo_id = kwargs.pop('pg_antigo_id', None)

        kwargs['pg1'] = kwargs.get('pg1', {'pg_antigo_id': pg_antigo_id}) 
        kwargs['pg2'] = kwargs.get('pg2', {'pg_antigo_id': pg_antigo_id})

        super(MultiplicacaoForm, self).__init__(*args, **kwargs)
        membros_choices = [(m.id, m.nome_completo) for m in Membro.query.order_by(Membro.nome_completo).all()]
        membros_choices.insert(0, (0, 'Selecione um membro'))
        
        self.pg1.facilitador.choices = membros_choices
        self.pg1.anfitriao.choices = membros_choices
        self.pg2.facilitador.choices = membros_choices
        self.pg2.anfitriao.choices = membros_choices

        self.pg1.setor.choices = []
        self.pg2.setor.choices = []

    def validate(self, **kwargs):
        valid_principal = super(MultiplicacaoForm, self).validate(**kwargs) 
        
        valid_pg1 = self.pg1.validate(self) 
        valid_pg2 = self.pg2.validate(self)

        return valid_principal and valid_pg1 and valid_pg2
