from typing import Any

from src.auth.authorization import require_access
from src.auth.claims import Principal
from src.common.errors import ForbiddenError, ValidationError
from src.common.responses import response, run_handler
from src.common.validation import parse_json_body
from src.pedidos.service import OrderService

_service = OrderService()
_READ_ROLES = {"Admin", "Operador", "Cliente"}


def listar_pedidos(event: dict[str, Any], context: Any) -> dict[str, Any]:
    return run_handler(event, "GET /pedidos", lambda: _list(event))


def obtener_pedido(event: dict[str, Any], context: Any) -> dict[str, Any]:
    return run_handler(event, "GET /pedidos/{id}", lambda: _get(event))


def crear_pedido(event: dict[str, Any], context: Any) -> dict[str, Any]:
    return run_handler(event, "POST /pedidos", lambda: _create(event))


def actualizar_estado_pedido(event: dict[str, Any], context: Any) -> dict[str, Any]:
    return run_handler(event, "PUT /pedidos/{id}/estado", lambda: _update_state(event))


def _list(event: dict[str, Any]) -> dict[str, Any]:
    principal = require_access(event, _READ_ROLES, "orders.read")
    customer_id = principal.customer_id if "Cliente" in principal.roles and not principal.roles.intersection({"Admin", "Operador"}) else None
    return response(200, _service.list_orders(customer_id=customer_id))


def _get(event: dict[str, Any]) -> dict[str, Any]:
    principal = require_access(event, _READ_ROLES, "orders.read")
    order = _service.get_order(_path_id(event))
    _require_ownership_if_customer(principal, order)
    return response(200, order)


def _create(event: dict[str, Any]) -> dict[str, Any]:
    principal = require_access(event, {"Cliente", "Operador"}, "orders.write")
    customer_name = principal.name or str(principal.claims.get("preferred_username") or "")
    order = _service.create_order(parse_json_body(event), customer_id=principal.customer_id, customer_name=customer_name)
    return response(201, order)


def _update_state(event: dict[str, Any]) -> dict[str, Any]:
    require_access(event, {"Admin", "Operador"}, "orders.write")
    body = parse_json_body(event)
    if set(body) != {"estado"}:
        raise ValidationError("El cuerpo debe contener únicamente estado.")
    return response(200, _service.update_state(_path_id(event), body["estado"]))


def _require_ownership_if_customer(principal: Principal, order: dict[str, Any]) -> None:
    if "Cliente" in principal.roles and not principal.roles.intersection({"Admin", "Operador"}):
        if order.get("clienteId") != principal.customer_id:
            raise ForbiddenError("Solo puedes consultar tus propios pedidos.")


def _path_id(event: dict[str, Any]) -> str:
    return str((event.get("pathParameters") or {}).get("id") or "")