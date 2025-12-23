from datetime import date, timedelta
from app.extensions import db
from .models import RegistroPresenca, PilulaDiaria
from calendar import monthrange
from sqlalchemy import func

def check_pilula_concluida_hoje(membro_id: int) -> bool:
    """Verifica se o membro já tem um RegistroPresenca de Pilula para hoje."""
    hoje = date.today()
    # Verifica se a pílula do dia existe E se o membro a concluiu
    pilula_do_dia = PilulaDiaria.query.filter_by(data_publicacao=hoje).first()
    
    if not pilula_do_dia:
        return True, None
        
    registro = RegistroPresenca.query.filter_by(
        membro_id=membro_id, 
        data=hoje, 
        tipo='Pilula', 
        pilula_id=pilula_do_dia.id
    ).first()
    
    return registro is not None, pilula_do_dia

def get_month_start_end(year: int, month: int) -> tuple[date, date]:
    """Retorna o primeiro e o último dia do mês especificado."""
    start_date = date(year, month, 1)
    _, num_days = monthrange(year, month)
    end_date = date(year, month, num_days)
    return start_date, end_date


def calcular_multiplicador_fidelidade(membro_id: int, data_final: date) -> float:
    """
    Calcula o Multiplicador de Fidelidade (Streak) baseado nas Pílulas Diárias
    completas nos últimos 7 dias que antecedem a data_final (inclusive).
    
    Regra: 5 Pílulas concluídas em 7 dias = x1.1. Menos que 5 = x1.0.
    """
    
    data_inicial = data_final - timedelta(days=6) # Últimos 7 dias (incluindo data_final)
    
    # Busca todos os registros de conclusão de Pílula no período
    pilulas_concluidas = RegistroPresenca.query.filter(
        RegistroPresenca.membro_id == membro_id,
        RegistroPresenca.tipo == 'Pilula',
        RegistroPresenca.data >= data_inicial,
        RegistroPresenca.data <= data_final
    ).all()
    
    # Contabiliza Pílulas Diárias Únicas (uma por dia)
    dias_com_pilula = set()
    for registro in pilulas_concluidas:
        dias_com_pilula.add(registro.data)
        
    num_dias_com_pilula = len(dias_com_pilula)
    
    # Aplica o multiplicador
    if num_dias_com_pilula >= 5:
        return 1.1 # 10% de bônus
    else:
        return 1.0 # Sem bônus

        
def calcular_monthly_pg_final(membro_id: int, year: int, month: int) -> int:
    """
    Calcula o Ponto Final (PG) total do mês para o membro, aplicando o 
    Multiplicador de Fidelidade semanal.
    
    PG Final = Soma(PG Base Semanal * Multiplicador Fidelidade)
    """
    start_date, end_date = get_month_start_end(year, month)
    pg_final_total = 0
    
    # Mapear o ponto base de cada dia para a sua semana (terminada no último dia da semana)
    current_date = start_date
    
    # Vamos agrupar os 7 dias de forma sequencial para o cálculo do multiplicador
    # e aplicar o multiplicador na pontuação daquela semana.
    
    while current_date <= end_date:
        # Define a janela semanal: do dia atual (current_date) até 6 dias no passado.
        # No entanto, a lógica do multiplicador é aplicada ao total de pontos da semana.
        
        # Para simplificar e evitar complexidade de "semana flutuante", vamos calcular 
        # a pontuação base acumulada em 7 dias (chunk) e aplicar o multiplicador
        # baseado no último dia do chunk.

        data_de_calculo = current_date
        week_start = current_date
        week_end = min(current_date + timedelta(days=6), end_date)
        
        # 1. Obter a Pontuação Base (PG) acumulada nesta semana (week_start a week_end)
        pg_base_semanal = db.session.query(func.sum(RegistroPresenca.pontuacao_ganha)).filter(
            RegistroPresenca.membro_id == membro_id,
            RegistroPresenca.data >= week_start,
            RegistroPresenca.data <= week_end
        ).scalar() or 0
        
        # 2. Obter o Multiplicador de Fidelidade (baseado no final da semana)
        multiplicador = calcular_multiplicador_fidelidade(membro_id, week_end)
        
        # 3. Adicionar PG Final para o total do mês
        pg_final_total += int(round(pg_base_semanal * multiplicador))
        
        # Avançar para a próxima semana
        current_date = week_end + timedelta(days=1)
        
    return pg_final_total
