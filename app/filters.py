from pytz import timezone, utc
from datetime import datetime
import locale

try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_ALL, 'pt_BR')
    except locale.Error:
        locale.setlocale(locale.LC_ALL, '')

def to_brasilia(value):
    if value is None:
        return ''
    if isinstance(value, datetime) and value.tzinfo is None:
        value = utc.localize(value)

    return value.astimezone(timezone('America/Sao_Paulo'))

def format_datetime(value, format="%d/%m/%Y %H:%M"):
    if value is None:
        return ''
    if isinstance(value, datetime):
        return value.strftime(format)
    return str(value)

def format_currency(value, symbol='R$', decimal_places=2):
    if value is None:
        return ''
    try:
        value = float(value)
        formatted_value = locale.format_string(f"%.{decimal_places}f", value, grouping=True)
        return f"{symbol} {formatted_value}"
    except (ValueError, TypeError):
        return str(value)
