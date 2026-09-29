from src.common.errors import ConflictError

ORDER_STATES = frozenset({"CREADO", "ACEPTADO", "EN_PREPARACION", "DESPACHADO", "ENTREGADO", "CANCELADO"})
_ALLOWED = {
    "CREADO": {"ACEPTADO", "CANCELADO"},
    "ACEPTADO": {"EN_PREPARACION", "CANCELADO"},
    "EN_PREPARACION": {"DESPACHADO", "CANCELADO"},
    "DESPACHADO": {"ENTREGADO"},
    "ENTREGADO": set(),
    "CANCELADO": set(),
}


def validate_transition(current: str, target: str) -> None:
    if target not in ORDER_STATES:
        from src.common.errors import ValidationError

        raise ValidationError("El estado indicado no es válido.")
    if target not in _ALLOWED.get(current, set()):
        raise ConflictError(f"No se puede cambiar un pedido de {current} a {target}.")