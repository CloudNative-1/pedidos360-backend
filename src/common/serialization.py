from datetime import date, datetime
from decimal import Decimal
from typing import Any


def json_default(value: Any) -> Any:
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    raise TypeError(f"Tipo no serializable: {type(value).__name__}")