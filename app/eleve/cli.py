# app/eleve/cli.py (Novo arquivo)

import click
from app.extensions import db
from .models import RegistroMensal
from datetime import datetime
from sqlalchemy import delete

# ====================================================================
# GRUPO DE COMANDOS CLI PARA O MÓDULO ELEVE
# ====================================================================

@click.group()
def eleve():
    """Comandos de manutenção e gestão do módulo ELEVE."""
    pass

@eleve.command('clean-monthly')
@click.argument('year', type=int, required=False, default=None)
def clean_monthly_records(year):
    """
    Deleta registros mensais (RegistroMensal) de anos anteriores ao atual, 
    mantendo apenas o histórico do ano vigente para otimização.
    
    Uso: flask eleve clean-monthly [ANO]
    Se [ANO] não for fornecido, usa o ano anterior ao atual.
    """
    
    current_year = datetime.now().year
    
    # Se o ano não for especificado, usamos o ano anterior ao atual.
    if year is None:
        target_year = current_year - 1
    else:
        target_year = year

    # Proteção: Não deletar registros do ano atual.
    if target_year >= current_year:
        click.echo(f"ERRO: A rotina de limpeza não pode deletar registros do ano vigente ({current_year}).")
        click.echo("Especifique um ano anterior ou use o padrão (ano anterior).")
        return

    click.echo(f"Iniciando limpeza dos registros mensais (RegistroMensal) do ano {target_year}...")

    try:
        # Contar registros a serem deletados
        records_to_delete = db.session.query(RegistroMensal).filter(RegistroMensal.ano == target_year).count()
        
        if records_to_delete == 0:
            click.echo(f"Nenhum registro mensal encontrado para o ano {target_year}. Limpeza finalizada.")
            return

        # Deletar os registros
        db.session.query(RegistroMensal).filter(RegistroMensal.ano == target_year).delete(synchronize_session='fetch')
        db.session.commit()
        
        click.echo(f"SUCESSO: {records_to_delete} registros mensais do ano {target_year} foram deletados do banco de dados.")

    except Exception as e:
        db.session.rollback()
        click.echo(f"ERRO DE BANCO DE DADOS: Não foi possível deletar os registros. {e}")

# Você pode adicionar outros comandos de manutenção ELEVE aqui.