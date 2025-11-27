import os
from datetime import datetime, timezone

basedir = os.path.abspath(os.path.dirname(__file__))

JORNADA_LIDERANCA_ALTERADA = {'class': 'bg-warning', 'icon': 'bi-person-badge', 'label': 'Liderança Alterada', 'categoria': 'Grupos'}
JORNADA_PARTICIPANTE_ADICIONADO_PG = {'class': 'bg-success', 'icon': 'bi-person-plus', 'label': 'Participante Adicionado', 'categoria': 'Grupos'}
JORNADA_PARTICIPANTE_REMOVIDO_PG = {'class': 'bg-danger', 'icon': 'bi-person-dash', 'label': 'Participante Removido', 'categoria': 'Grupos'}
JORNADA_INDICADORES_PG_ATUALIZADOS = {'class': 'bg-info', 'icon': 'bi-bar-chart-line', 'label': 'Indicadores Atualizados', 'categoria': 'Grupos'}
JORNADA_CADASTRO_MEMBRO = {'class': 'bg-success', 'icon': 'bi-person-add', 'label': 'Membro Cadastrado', 'categoria': 'Membresia'}
JORNADA_MEMBRO_ATUALIZADO = {'class': 'bg-info', 'icon': 'bi-pencil', 'label': 'Membro Atualizado', 'categoria': 'Membresia'}
JORNADA_MEMBRO_ATUALIZADO_SELF = {'class': 'bg-info', 'icon': 'bi-pencil', 'label': 'Perfil Atualizado', 'categoria': 'Membresia'}
JORNADA_DESLIGAMENTO = {'class': 'bg-danger', 'icon': 'bi-person-x', 'label': 'Desligamento', 'categoria': 'Membresia'}
JORNADA_CONTRIBUICAO = {'class': 'bg-primary', 'icon': 'bi-currency-dollar', 'label': 'Contribuição', 'categoria': 'Financeiro'}
JORNADA_AREA_CRIADA = {'class': 'bg-primary', 'icon': 'bi-plus-circle', 'label': 'Área Criada', 'categoria': 'Grupos'}
JORNADA_CONCLUSAO_CTM = {'class': 'bg-success', 'icon': 'bi-award', 'label': 'Conclusão de Ciclo', 'categoria': 'CTM'}
JORNADA_CONCLUSAO_EVENTO = {'class': 'bg-success', 'icon': 'bi-award', 'label': 'Conclusão de Evento', 'categoria': 'Eventos'}
JORNADA_REPROVACAO_CTM = {'class': 'bg-danger', 'icon': 'bi-x-circle', 'label': 'Reprovação de Ciclo', 'categoria': 'CTM'}
JORNADA_TURMA_ARQUIVADA = {'class': 'bg-secondary', 'icon': 'bi-archive-fill', 'label': 'Turma Arquivada', 'categoria': 'CTM'}
JORNADA_NOVO_MEMBRO = {'class': 'bg-success', 'icon': 'bi-person-plus', 'label': 'Participante recebido como Membro', 'categoria': 'Membresia'}
JORNADA_PRESENCA_CTM = {'class': 'bg-info', 'icon': 'bi-bar-chart-line', 'label': 'Participante Presente no CTM', 'categoria': 'Membresia'}
JORNADA_MULTIPLICACAO = {'class': 'bg-success', 'icon': 'bi-award', 'label': 'Multiplicação de PG', 'categoria': 'Grupos'}
JORNADA_PG_FECHADO = {'class': 'bg-danger', 'icon': 'bi-x-octagon-fill', 'label': 'PG Fechado', 'categoria': 'Grupos'}
JORNADA_PRESENCA_CTM_REMOVIDA = {'class': 'bg-danger', 'icon': 'bi-person-dash', 'label': 'Presença CTM Removida', 'categoria': 'CTM'}
JORNADA_CONTRIBUICAO_EXCLUIDA = {'class': 'bg-danger', 'icon': 'bi-trash', 'label': 'Receita Excluída', 'categoria': 'Financeiro'}
JORNADA_DESPESA_EXCLUIDA = {'class': 'bg-danger', 'icon': 'bi-trash', 'label': 'Despesa Excluída', 'categoria': 'Financeiro'}

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'chave-secreta-segura'

    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(os.path.abspath(os.path.join(basedir, os.pardir)), 'data', 'iban.db')

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    TIMEZONE = 'America/Sao_Paulo'
    VERSAO_APP = '2.9.11 - Responsividade'
    ANO_ATUAL = datetime.now().year

    ID_OFERTA_ANONIMA = 90000

    CORES_CAMPUS = {
        'Central':        '#0d6efd',
        'Concesso Elias': "#20c997",
        'Capão':          '#198754',
        'Cidade Nova':    '#dc3545',
        'Perdigão':       '#ffc107',
        'Pitangui':       '#0dcaf0',
    }

    CORES_STATUS = {
        'Facilitador em Treinamento': '#20c997',
        'Anfitrião em Treinamento':   '#0dcaf0',
        'Anfitrião de PG':    '#0d6efd',
        'Facilitador de PG':  '#198754',
        'Supervisor de Setor':   '#ffc107',
        'Supervisor de Área':       '#dc3545',  
        'Sem Cargo':   "#6c757d", 
    }

    CAMPUS = [
    'Central', 'Concesso Elias', 'Capão',
    'Cidade Nova', 'Perdigão', 'Pitangui'
    ]
    
    CENTROS_DE_CUSTO = ['Geral'] + CAMPUS
    
    STATUS = [
    'Membro', 'Líder', 'Supervisor', 'Não-Membro'
    ]

    TIPOS = ['Dízimo', 'Oferta', 'Oferta Missionária']
    
    TIPOS_DESPESA = ['Fixa', 'Variável']

    FORMAS = ['via Pix', 'em Espécie', 'Boleto', 'Débito']

    RECORRENCIAS = ['Isolada', 'Semanal', 'Quinzenal', 'Mensal']

    JORNADA = {
        'LIDERANCA_ALTERADA': JORNADA_LIDERANCA_ALTERADA,
        'PARTICIPANTE_ADICIONADO_PG': JORNADA_PARTICIPANTE_ADICIONADO_PG,
        'PARTICIPANTE_REMOVIDO_PG': JORNADA_PARTICIPANTE_REMOVIDO_PG,
        'INDICADORES_PG_ATUALIZADOS': JORNADA_INDICADORES_PG_ATUALIZADOS,
        'CADASTRO_MEMBRO': JORNADA_CADASTRO_MEMBRO,
        'MEMBRO_ATUALIZADO': JORNADA_MEMBRO_ATUALIZADO,
        'MEMBRO_ATUALIZADO_SELF': JORNADA_MEMBRO_ATUALIZADO_SELF,
        'DESLIGAMENTO': JORNADA_DESLIGAMENTO,
        'CADASTRO_NAO_MEMBRO': JORNADA_CADASTRO_MEMBRO,
        'CADASTRO_NAO_MEMBRO_E_INSCRICAO': JORNADA_CADASTRO_MEMBRO,
        'CONTRIBUICAO': JORNADA_CONTRIBUICAO,
        'PG_FECHADO': JORNADA_PG_FECHADO,
        'PRESENCA_CTM_REMOVIDA': JORNADA_PRESENCA_CTM_REMOVIDA,
        'AREA_CRIADA': JORNADA_AREA_CRIADA,
        'CONCLUSAO_CTM': JORNADA_CONCLUSAO_CTM,
        'REPROVACAO_CTM': JORNADA_REPROVACAO_CTM,
        'TURMA_ARQUIVADA': JORNADA_TURMA_ARQUIVADA,
        'PARTICIPANTE_ADICIONADO_CTM': JORNADA_PARTICIPANTE_ADICIONADO_PG,
        'MEMBRO_RECEBIDO': JORNADA_NOVO_MEMBRO,
        'EVENTO_CONCLUIDO': JORNADA_CONCLUSAO_EVENTO,
        'PRESENCA_CTM': JORNADA_PRESENCA_CTM,
        'PG_MULTIPLICADO': JORNADA_MULTIPLICACAO,
        'CONTRIBUICAO_EXCLUIDA': JORNADA_CONTRIBUICAO_EXCLUIDA,
        'DESPESA_EXCLUIDA': JORNADA_DESPESA_EXCLUIDA,
    }
