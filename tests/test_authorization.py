from typing import Any

import pytest

from src.auth.claims import get_claims, get_principal
from src.catalogo import handlers as catalog_handlers
from src.common.errors import ValidationError
from src.pedidos import handlers as order_handlers
from src.pedidos.service import OrderService


def _event(*, roles: list[str], scopes: str) -> dict[str, Any]:
    return {
        "requestContext": {
            "authorizer": {
                "jwt": {
                    "claims": {"sub": "subject-1", "oid": "customer-1", "roles": roles, "scp": scopes},
                    "scopes": scopes.split(),
                }
            }
        }
    }


def test_claims_are_read_from_http_api_jwt_context() -> None:
    event = _event(roles=["Auditor"], scopes="catalog.read orders.read")

    assert get_claims(event)["sub"] == "subject-1"
    principal = get_principal(event)
    assert principal is not None
    assert principal.customer_id == "customer-1"
    assert principal.roles == frozenset({"Auditor"})
    assert principal.scopes == frozenset({"catalog.read", "orders.read"})


def test_missing_principal_returns_401() -> None:
    result = catalog_handlers.listar_catalogo({}, None)

    assert result["statusCode"] == 401
    assert '"error": "UNAUTHORIZED"' in result["body"]


def test_admin_and_operator_can_read_catalog_but_customer_cannot(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(catalog_handlers._service, "list_products", lambda: [])

    for role in ("Admin", "Operador"):
        result = catalog_handlers.listar_catalogo(_event(roles=[role], scopes="catalog.read"), None)
        assert result["statusCode"] == 200

    result = catalog_handlers.listar_catalogo(_event(roles=["Cliente"], scopes="catalog.read"), None)
    assert result["statusCode"] == 403


def test_missing_scope_returns_403(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(catalog_handlers._service, "list_products", lambda: [])

    result = catalog_handlers.listar_catalogo(_event(roles=["Admin"], scopes="orders.read"), None)

    assert result["statusCode"] == 403


def test_auditor_is_outside_current_business_routes() -> None:
    event = _event(roles=["Auditor"], scopes="catalog.read orders.read")

    assert catalog_handlers.listar_catalogo(event, None)["statusCode"] == 403
    assert order_handlers.listar_pedidos(event, None)["statusCode"] == 403


def test_operator_catalog_write_is_currently_allowed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(catalog_handlers._service, "create_product", lambda payload: {"id": payload["nombre"]})
    event = _event(roles=["Operador"], scopes="catalog.write")
    event["body"] = '{"nombre":"Producto","precio":1,"stock":1}'

    assert catalog_handlers.crear_producto(event, None)["statusCode"] == 201


def test_customer_order_list_is_scoped_to_jwt_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    requested: dict[str, Any] = {}

    def list_orders(*, customer_id: str | None = None) -> list[dict[str, Any]]:
        requested["customer_id"] = customer_id
        return []

    monkeypatch.setattr(order_handlers._service, "list_orders", list_orders)
    result = order_handlers.listar_pedidos(_event(roles=["Cliente"], scopes="orders.read"), None)

    assert result["statusCode"] == 200
    assert requested["customer_id"] == "customer-1"


def test_customer_cannot_read_another_customers_order(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(order_handlers._service, "get_order", lambda order_id: {"id": order_id, "clienteId": "other"})
    event = _event(roles=["Cliente"], scopes="orders.read")
    event["pathParameters"] = {"id": "order-1"}

    result = order_handlers.obtener_pedido(event, None)

    assert result["statusCode"] == 403


def test_customer_can_read_own_order(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(order_handlers._service, "get_order", lambda order_id: {"id": order_id, "clienteId": "customer-1"})
    event = _event(roles=["Cliente"], scopes="orders.read")
    event["pathParameters"] = {"id": "order-1"}

    assert order_handlers.obtener_pedido(event, None)["statusCode"] == 200


def test_customer_cannot_change_order_state() -> None:
    event = _event(roles=["Cliente"], scopes="orders.write")
    event.update({"pathParameters": {"id": "order-1"}, "body": '{"estado":"ACEPTADO"}'})

    assert order_handlers.actualizar_estado_pedido(event, None)["statusCode"] == 403


def test_customer_identity_comes_from_jwt_not_request_body(monkeypatch: pytest.MonkeyPatch) -> None:
    class Repository:
        order: dict[str, Any] | None = None

        def get_product(self, product_id: str) -> dict[str, Any]:
            return {"id": product_id, "nombre": "Té", "precio": 10, "stock": 5}

        def create_order(self, order: dict[str, Any]) -> None:
            self.order = order

    repository = Repository()
    monkeypatch.setattr(order_handlers, "_service", OrderService(repository))
    event = _event(roles=["Cliente"], scopes="orders.write")
    event["requestContext"]["authorizer"]["jwt"]["claims"]["name"] = "Nombre del token"
    event["body"] = '{"productos":[{"productoId":"p-1","cantidad":1}]}'

    result = order_handlers.crear_pedido(event, None)

    assert result["statusCode"] == 201
    assert repository.order is not None
    assert repository.order["clienteId"] == "customer-1"
    assert repository.order["clienteNombre"] == "Nombre del token"

    event["body"] = '{"productos":[{"productoId":"p-1","cantidad":1}],"clienteId":"spoofed"}'
    assert order_handlers.crear_pedido(event, None)["statusCode"] == 400


@pytest.mark.parametrize("role", ["Admin", "Operador"])
def test_admin_and_operator_can_change_order_state(monkeypatch: pytest.MonkeyPatch, role: str) -> None:
    monkeypatch.setattr(order_handlers._service, "update_state", lambda order_id, state: {"id": order_id, "estado": state})
    event = _event(roles=[role], scopes="orders.write")
    event.update({"pathParameters": {"id": "order-1"}, "body": '{"estado":"ACEPTADO"}'})

    assert order_handlers.actualizar_estado_pedido(event, None)["statusCode"] == 200


def test_order_rejects_more_than_99_distinct_products() -> None:
    class Repository:
        def get_product(self, product_id: str) -> None:
            pytest.fail(f"No debe consultar el producto {product_id} antes de validar el límite transaccional.")

    payload = {"productos": [{"productoId": str(index), "cantidad": 1} for index in range(100)]}

    with pytest.raises(ValidationError):
        OrderService(Repository()).create_order(payload, customer_id="customer-1", customer_name="")