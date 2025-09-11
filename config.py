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
JORNADA_REPROVACAO_CTM = {'class': 'bg-danger', 'icon': 'bi-x-circle', 'label': 'Reprovação de Ciclo', 'categoria': 'CTM'}
JORNADA_TURMA_ARQUIVADA = {'class': 'bg-secondary', 'icon': 'bi-archive-fill', 'label': 'Turma Arquivada', 'categoria': 'CTM'}

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'chave-secreta-segura'

    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(os.path.abspath(os.path.join(basedir, os.pardir)), 'data', 'iban.db')

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    TIMEZONE = 'America/Sao_Paulo'
    VERSAO_APP = '2.6.1 - Cadastros Duplicados'
    ANO_ATUAL = datetime.now().year

    IDS_OFERTA_ANONIMA_POR_CAMPUS = {
        'Central': 90001,
        'Concesso Elias': 90002,
        'Capão': 90003,
        'Cidade Nova': 90004,
        'Perdigão': 90005,
        'Pitangui': 90006,
        'Desconhecido': 90000
    }

    CAMPUS = {
        'Central':        '#0d6efd',
        'Concesso Elias': '#6c757d',
        'Capão':          '#198754',
        'Cidade Nova':    '#dc3545',
        'Perdigão':       '#ffc107',
        'Pitangui':       '#0dcaf0',
    }

    STATUS = {
        'Anfitrião':    '#0d6efd',
        'Líder':  '#198754',
        'Supervisor':   '#ffc107',
        #'Pastor':       '#dc3545',  
        'Não-Membro':   '#6c757d', 
        #'Inativo':      '#6c757d',
    }

    TIPOS = ['Dízimo', 'Oferta']

    FORMAS = ['via Pix', 'em Espécie']

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
        'CONTRIBUICAO': JORNADA_CONTRIBUICAO,
        'AREA_CRIADA': JORNADA_AREA_CRIADA,
        'CONCLUSAO_CTM': JORNADA_CONCLUSAO_CTM,
        'REPROVACAO_CTM': JORNADA_REPROVACAO_CTM,
        'TURMA_ARQUIVADA': JORNADA_TURMA_ARQUIVADA,
        'PARTICIPANTE_ADICIONADO_CTM': JORNADA_PARTICIPANTE_ADICIONADO_PG,
    }
