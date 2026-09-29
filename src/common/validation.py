import json
from decimal import Decimal, InvalidOperation
from typing import Any

from src.common.errors import ValidationError


def parse_json_body(event: dict[str, Any]) -> dict[str, Any]:
    body = event.get("body")
    if not isinstance(body, str):
        raise ValidationError("El cuerpo de la solicitud debe ser un objeto JSON.")
    try:
        value = json.loads(body)
    except json.JSONDecodeError as error:
        raise ValidationError("El cuerpo de la solicitud no contiene JSON válido.") from error
    if not isinstance(value, dict):
        raise ValidationError("El cuerpo de la solicitud debe ser un objeto JSON.")
    return value


def decimal_value(value: Any, field: str, *, minimum: Decimal = Decimal("0")) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        raise ValidationError(f"{field} debe ser un número.")
    try:
        result = Decimal(str(value))
    except InvalidOperation as error:
        raise ValidationError(f"{field} debe ser un número válido.") from error
    if not result.is_finite() or result < minimum:
        raise ValidationError(f"{field} debe ser mayor o igual a {minimum}.")
    return result


def integer_value(value: Any, field: str, *, minimum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValidationError(f"{field} debe ser un entero mayor o igual a {minimum}.")
    return value