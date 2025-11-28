from flask_wtf import FlaskForm
from wtforms import SelectField, SubmitField, DateField, FloatField, TextAreaField, StringField
from wtforms.validators import DataRequired, NumberRange, Optional, ValidationError, Length
from config import Config
from app.membresia.models import Membro
from datetime import date
from .models import Contribuicao, CategoriaDespesa, ItemDespesa, Despesa
from app.extensions import db

def coerce_to_int_or_none(value):
    if value == '':
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None

class ContribuicaoForm(FlaskForm):
    membro_id = SelectField('Membro', coerce=coerce_to_int_or_none, validators=[DataRequired()])
    tipo = SelectField('Tipo', choices=[(t, t) for t in Config.TIPOS], validators=[DataRequired()])
    valor = FloatField('Valor (R$)', validators=[DataRequired(), NumberRange(min=0.01)])
    data_lanc = DateField('Data', validators=[DataRequired()])
    forma = SelectField('Forma de Contribuição', choices=[(f, f) for f in Config.FORMAS], validators=[DataRequired()])
    centro_custo = SelectField('Centro de Custo', validators=[DataRequired(message="Selecione um centro de custo.")])
    observacoes = TextAreaField('Observações', render_kw={'rows': 3})
    submit = SubmitField('Lançar Contribuição')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tipo.choices = [(t, t) for t in Config.TIPOS]
        self.forma.choices = [(f, f) for f in Config.FORMAS]

        todos_ccs = Config.CENTROS_DE_CUSTO
        ccs_receitas = [c for c in todos_ccs if c != 'Geral']

        self.centro_custo.choices = [(c, c) for c in ccs_receitas]
        self.centro_custo.choices.insert(0, ('', 'Selecione o Centro de Custo'))

    def validate_data_lanc(self, field):
        if field.data > date.today():
            raise ValidationError('A data de lançamento não pode ser futura.')

class ContribuicaoFilterForm(FlaskForm):
    csrf_enabled = False
    
    busca_nome = StringField('Por nome', validators=[Optional()])
    tipo_filtro = SelectField('Por Tipo', validators=[Optional()])
    status_filtro = SelectField('Por Status', validators=[Optional()])
    centro_custo_filtro = SelectField('Por Centro de Custo', validators=[Optional()])
    data_inicial = DateField('Data Inicial', format='%Y-%m-%d', validators=[Optional()])
    data_final = DateField('Data Final', format='%Y-%m-%d', validators=[Optional()])
    submit_filter = SubmitField('Filtrar')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tipo_filtro.choices = [('', 'Todos os Tipos')] + [(t, t) for t in Config.TIPOS]
        self.status_filtro.choices = [('', 'Todos os Status')] + [(s, s) for s in Config.STATUS]
        self.centro_custo_filtro.choices = [('', 'Todos os Centros de Custo')] + [(c, c) for c in Config.CENTROS_DE_CUSTO]

class CategoriaDespesaForm(FlaskForm):
    codigo = StringField('Código Contábil', validators=[Optional(), Length(max=20)])
    nome = StringField('Nome da Categoria', validators=[DataRequired(), Length(max=100)])
    submit = SubmitField('Salvar Categoria')

    def validate_nome(self, nome):
        categoria = CategoriaDespesa.query.filter_by(nome=nome.data).first()
        if categoria:
            raise ValidationError('Esta categoria já existe.')

class ItemDespesaForm(FlaskForm):
    categoria_id = SelectField('Categoria', coerce=coerce_to_int_or_none, validators=[DataRequired(message="Por favor, selecione uma categoria.")])
    codigo = StringField('Código Contábil', validators=[Optional(), Length(max=20)])
    nome = StringField('Nome do Item', validators=[DataRequired(), Length(max=150)])
    tipo_fixa_variavel = SelectField('Tipo', choices=[(t, t) for t in Config.TIPOS_DESPESA], validators=[DataRequired()])
    submit = SubmitField('Salvar Item')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.categoria_id.choices = [(c.id, c.nome) for c in CategoriaDespesa.query.order_by(CategoriaDespesa.nome).all()]
        self.categoria_id.choices.insert(0, ('', 'Selecione a Categoria'))

    def validate_nome(self, nome):
        item = ItemDespesa.query.filter_by(nome=nome.data, categoria_id=self.categoria_id.data).first()
        if item:
            raise ValidationError('Este item já existe nesta categoria.')

class DespesaForm(FlaskForm):
    item_id = SelectField('Conta / Item de Despesa', coerce=coerce_to_int_or_none, validators=[DataRequired(message="Por favor, selecione uma conta.")])
    valor = FloatField('Valor (R$)', validators=[DataRequired(), NumberRange(min=0.01)])
    centro_custo = SelectField('Centro de Custo', validators=[DataRequired(message="Selecione um centro de custo.")])
    data_lanc = DateField('Data de Competência', validators=[DataRequired(), lambda form, field: (
        True if field.data <= date.today() else ValidationError('A data de lançamento não pode ser futura.')
    )])
    situacao = SelectField('Situação', choices=[('pago', 'Pago (Realizado)'), ('pendente', 'A Pagar (Agendado)')], validators=[DataRequired()])
    data_vencimento = DateField('Data de Vencimento', validators=[Optional()])
    recorrencia = SelectField('Recorrência', validators=[DataRequired()], choices=[(r, r) for r in Config.RECORRENCIAS])
    observacoes = TextAreaField('Histórico / Observações', render_kw={'rows': 3})
    submit = SubmitField('Confirmar Lançamento')

    def __init__(self, *args, **kwargs): 
        super().__init__(*args, **kwargs)
        
        itens = ItemDespesa.query.join(CategoriaDespesa).order_by(
            CategoriaDespesa.codigo, 
            ItemDespesa.codigo, 
            ItemDespesa.nome
        ).all()
        
        self.centro_custo.choices = [('', 'Selecione o Centro de Custo')] + [(c, c) for c in Config.CENTROS_DE_CUSTO]
        
        self.item_id.choices = [
            (item.id, f"{item.codigo if item.codigo else 'S/C'} - {item.nome}") for item in itens
        ]
        self.recorrencia.choices = [(r, r) for r in Config.RECORRENCIAS]
        self.item_id.choices.insert(0, ('', 'Selecione a conta contábil'))

class DespesaFilterForm(FlaskForm):
    csrf_enabled = False
    
    categoria_filtro = SelectField('Filtro por Categoria', coerce=coerce_to_int_or_none, validators=[Optional()])
    item_filtro = SelectField('Por Item', coerce=coerce_to_int_or_none, validators=[Optional()])
    recorrencia_filtro = SelectField('Por Recorrência', validators=[Optional()])
    centro_custo_filtro = SelectField('Por Centro de Custo', validators=[Optional()])
    data_inicial = DateField('Data Inicial', format='%Y-%m-%d', validators=[Optional()])
    data_final = DateField('Data Final', format='%Y-%m-%d', validators=[Optional()])
    submit_filter = SubmitField('Filtrar')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.categoria_filtro.choices = [('', 'Todas as Categorias')] + \
                                        [(c.id, c.nome) for c in CategoriaDespesa.query.order_by(CategoriaDespesa.nome).all()]
        self.item_filtro.choices = [('', 'Todos os Itens')]
        self.recorrencia_filtro.choices = [('', 'Todas as Recorrências')] + [(r, r) for r in Config.RECORRENCIAS]
        self.centro_custo_filtro.choices = [('', 'Todos os Centros de Custo')] + [(c, c) for c in Config.CENTROS_DE_CUSTO]
