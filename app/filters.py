from datetime import datetime, timezone
from pytz import timezone as pytz_timezone, utc
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
    if not isinstance(value, datetime):
        return str(value)

    if value.tzinfo is None:
        value_utc_aware = utc.localize(value)
    else:
        value_utc_aware = value.astimezone(utc)
    
    brasilia_tz = pytz_timezone('America/Sao_Paulo')
    return value_utc_aware.astimezone(brasilia_tz)

def format_datetime(value, format="%d/%m/%Y %H:%M"):
    if value is None:
        return ''
    if not isinstance(value, datetime):
        return str(value)
    dt_brasilia = to_brasilia(value)
    return dt_brasilia.strftime(format)


def format_currency(value, symbol='R$', decimal_places=2):
    if value is None:
        return ''
    try:
        value = float(value)
        formatted_value = locale.format_string(f"%.{decimal_places}f", value, grouping=True)
        return f"{symbol} {formatted_value}"
    except (ValueError, TypeError):
        return str(value)
