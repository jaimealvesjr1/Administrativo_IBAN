import os
from datetime import datetime

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'chave-secreta-segura'

    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(os.path.abspath(os.path.join(basedir, os.pardir)), 'data', 'iban.db')

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    VERSAO_APP = 'Beta v1.1'
    ANO_ATUAL = datetime.now().year

    IDS_OFERTA_ANONIMA_POR_CAMPUS = {
        'Central':            90001,
        'Concesso Elias':     90002,
        'Capão':              90003,
        'Cidade Nova':        90004,
        'Perdigão':           90005,
        'Pitangui':           90006,
        'Desconhecido':       90000
    }

    AVAILABLE_PERMISSIONS = [
        'admin',        # Acesso total a áreas administrativas e gerenciamento de usuários
        'membro',       # Permissão padrão para membros registrados
    ]

    CAMPUS = {
        'Central':        '#0d6efd',  # primary
        'Concesso Elias': '#6c757d',  # secondary
        'Capão':          '#198754',  # success
        'Cidade Nova':    '#dc3545',  # danger
        'Perdigão':       '#ffc107',  # warning
        'Pitangui':       '#0dcaf0',  # info
    #   'Outro':          '#6f42c1',    # purple
    }

    STATUS = {
        'Membro':       '#0d6efd',  # primary
        'Líder':        '#198754',  # success
        'Supervisor':   '#ffc107',  # warning
        'Não-Membro':   '#dc3545',  # danger
        'Inativo':      '#6c757d',  # secondary
    }

    TIPOS = ['Dízimo', 'Oferta'] #'Oferta Missionária'

    FORMAS = ['via Pix', 'em Espécie']

    JORNADA_CADASTRO_MEMBRO = {
        'class': 'bg-secondary', 'icon': 'bi-person-add',
        'label': 'Cadastro', 'categoria': 'Admissão'
    }

    JORNADA_CADASTRO_CTM = {
        'class': 'bg-secondary', 'icon': 'bi-person-fill-add',
        'label': 'Ingresso no CTM', 'categoria': 'Admissão'
    }

    JORNADA = {
        'Cadastro': JORNADA_CADASTRO_MEMBRO,

        'Status_Mudanca': {
            'class': 'bg-warning', 'icon': 'bi-person-check',
            'label': 'Mudança de Status', 'categoria': 'Atualizações'
        },

        'Campus_Mudanca': {
            'class': 'bg-warning', 'icon': 'bi-building',
            'label': 'Mudança de Campus', 'categoria': 'Atualizações'
        },

        'Desligamento': {
            'class': 'bg-danger', 'icon': 'bi-person-x',
            'label': 'Desligamento', 'categoria': 'Saída'
        },

        'Data_Recepcao_Mudanca': {
            'class': 'bg-warning', 'icon': 'bi-calendar-event',
            'label': 'Data Recepção Alterada', 'categoria': 'Atualizações'
        },

        'Cadastro_Nao_Membro_CTM': JORNADA_CADASTRO_CTM,

        'Presenca': {
            'class': 'bg-success', 'icon': 'bi-check-circle',
            'label': 'Presença no CTM', 'categoria': 'Frequência'
        },

        'Contribuicao': {
            'class': 'bg-primary', 'icon': 'bi-currency-dollar',
            'label': 'Contribuição', 'categoria': 'Financeiro'
        },
    }
