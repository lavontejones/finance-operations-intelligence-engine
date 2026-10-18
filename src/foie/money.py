"""Exact USD controls; reject invalid or sub-cent inputs rather than round them."""
import re
from decimal import Decimal, InvalidOperation


def money(value):
    try:
        result = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError("Invalid monetary amount") from exc
    if not result.is_finite() or abs(result) > Decimal(1000000000000):
        raise ValueError("Non-finite or excessive monetary amount")
    if result != result.quantize(Decimal("0.01")):
        raise ValueError("Sub-cent amount requires source correction")
    return result.quantize(Decimal("0.01"))
def csv_cell(value):
    if isinstance(value, str):
        s=value.lstrip()
        if s.startswith(("=", "+", "-", "@")) and not re.fullmatch(r"-?[0-9]+(?:\.[0-9]+)?",s):
            return "'"+value
        if value.startswith(("\t","\r","\n")):
            return "'"+value
    return value
