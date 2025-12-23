from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, SubmitField, FormField, BooleanField, DateField
from wtforms.validators import DataRequired, Length, Optional, URL, ValidationError
from app.eleve.models import RODA_DA_VIDA_SUBCATEGORIAS
from datetime import date
from collections import OrderedDict # Para garantir a ordem das opções

# ====================================================================
# FORMULÁRIO PRINCIPAL DA PÍLULA (SIMPLIFICADO)
# ====================================================================

class PilulaDiariaForm(FlaskForm):
    
    # --- 1. DETALHES PRINCIPAIS ---
    titulo = StringField('Título da Pílula', 
                         validators=[DataRequired(), Length(min=5, max=100)])

    data_publicacao = DateField('Data de Publicação (Prazo)', 
                                format='%Y-%m-%d',
                                default=date.today,
                                validators=[DataRequired()],
                                description='Dia exato em que a Pílula estará disponível. Não pode ser retroativa.')
    
    subcategoria_rv = SelectField('Subcategoria da Roda da Vida (RV)',
                                  choices=[(c, c) for c in RODA_DA_VIDA_SUBCATEGORIAS],
                                  validators=[DataRequired()])
    
    link_video = StringField('Link do Vídeo (URL do YouTube)',
                             validators=[Optional(), URL()],
                             description='URL do vídeo (2 Pontos Base).')

    descricao_tarefa = TextAreaField('Descrição da Tarefa (Ação Prática)',
                                     validators=[Optional()],
                                     description='Descrição breve da Tarefa (2 Pontos Base).')
    
    # --- 2. QUIZ SIMPLIFICADO (APENAS UMA PERGUNTA DE 4 ALTERNATIVAS) ---
    # Nota: Simplificamos para 1 pergunta, seguindo o requisito de focar em uma estrutura funcional.
    
# PERGUNTA 1 (OBRIGATÓRIO PREENCHER PARA VALIDAÇÃO)
    quiz_p1 = StringField('Pergunta 1 do Quiz', validators=[Optional(), Length(max=255)])
    alt_a1 = StringField('Alternativa A', validators=[Optional(), Length(max=255)])
    alt_b1 = StringField('Alternativa B', validators=[Optional(), Length(max=255)])
    alt_c1 = StringField('Alternativa C', validators=[Optional(), Length(max=255)])
    alt_d1 = StringField('Alternativa D', validators=[Optional(), Length(max=255)])
    quiz_c1 = SelectField('Correta 1', 
                           choices=[('', '---'), ('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D')],
                           validators=[Optional()])
                           
    # PERGUNTA 2
    quiz_p2 = StringField('Pergunta 2 do Quiz', validators=[Optional(), Length(max=255)])
    alt_a2 = StringField('Alternativa A', validators=[Optional(), Length(max=255)])
    alt_b2 = StringField('Alternativa B', validators=[Optional(), Length(max=255)])
    alt_c2 = StringField('Alternativa C', validators=[Optional(), Length(max=255)])
    alt_d2 = StringField('Alternativa D', validators=[Optional(), Length(max=255)])
    quiz_c2 = SelectField('Correta 2', 
                           choices=[('', '---'), ('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D')],
                           validators=[Optional()])
                           
    # PERGUNTA 3
    quiz_p3 = StringField('Pergunta 3 do Quiz', validators=[Optional(), Length(max=255)])
    alt_a3 = StringField('Alternativa A', validators=[Optional(), Length(max=255)])
    alt_b3 = StringField('Alternativa B', validators=[Optional(), Length(max=255)])
    alt_c3 = StringField('Alternativa C', validators=[Optional(), Length(max=255)])
    alt_d3 = StringField('Alternativa D', validators=[Optional(), Length(max=255)])
    quiz_c3 = SelectField('Correta 3', 
                           choices=[('', '---'), ('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D')],
                           validators=[Optional()])
        
    submit = SubmitField('Salvar Pílula')
    
    # --- 3. VALIDAÇÕES CUSTOMIZADAS ---

    def validate(self, extra_validators=None):
        initial_validation = super().validate(extra_validators)
        if not initial_validation:
            return False

        # Validações Específicas do Quiz
        if not self._validate_quiz_question(self.quiz_p1, self.alt_a1, self.alt_b1, self.alt_c1, self.alt_d1, self.quiz_c1):
            return False
            
        if not self._validate_quiz_question(self.quiz_p2, self.alt_a2, self.alt_b2, self.alt_c2, self.alt_d2, self.quiz_c2):
            return False
            
        # CORREÇÃO AQUI: self.alt_p3 mudou para self.alt_a3
        if not self._validate_quiz_question(self.quiz_p3, self.alt_a3, self.alt_b3, self.alt_c3, self.alt_d3, self.quiz_c3):
            return False

        return True

    def _validate_quiz_question(self, pergunta_field, alt_a, alt_b, alt_c, alt_d, correta_field):
        """Helper para validar uma única pergunta do quiz, suas 4 alternativas e a resposta correta."""
        
        # A validação SÓ ocorre se a pergunta for preenchida
        if pergunta_field.data:
            alternativas = [alt_a.data, alt_b.data, alt_c.data, alt_d.data]
            
            # 1. CHECK OBRIGATORIEDADE DE TODAS AS 4 ALTERNATIVAS
            if not all(alt for alt in alternativas):
                pergunta_field.errors.append('Se a pergunta for preenchida, é obrigatório preencher TODAS as 4 alternativas.')
                return False

            # 2. CHECK RESPOSTA CORRETA SELECIONADA
            if not correta_field.data:
                pergunta_field.errors.append('Se a pergunta for preenchida, você deve selecionar qual alternativa está correta.')
                return False
                
        return True
        
    def validate_data_publicacao(self, field):
        from app.eleve.models import PilulaDiaria, db
        from datetime import date
        
        if field.data and field.data < date.today():
             raise ValidationError('A data de publicação não pode ser retroativa.')

        query = PilulaDiaria.query.filter_by(data_publicacao=field.data)
        
        if hasattr(self, 'pilula_id') and self.pilula_id:
            query = query.filter(PilulaDiaria.id != self.pilula_id)
            
        if query.first():
            raise ValidationError('Já existe uma Pílula Diária cadastrada para esta data. Só é permitida uma por dia.')

class RegistroPresencaDiariaForm(FlaskForm):
    
    # Campo para buscar e selecionar o membro (será integrado com Select2/AJAX)
    membro_nome = StringField('Buscar Discípulo (Nome Completo)', 
                              validators=[DataRequired(), Length(min=5)],
                              description='Comece a digitar o nome do membro para buscar.')

    data = DateField('Data da Presença', 
                     format='%Y-%m-%d',
                     default=date.today,
                     validators=[DataRequired()])
    
    # Checkboxes para as atividades (baseado nos pontos do documento)
    culto = BooleanField('Presença em Culto (5 Pontos)', default=False)
    pg = BooleanField('Presença em PG (Pequeno Grupo) (5 Pontos)', default=False)
    servico = BooleanField('Serviço em Departamento (3 Pontos)', default=False)
    
    submit = SubmitField('Registrar Presenças')
