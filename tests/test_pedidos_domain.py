from decimal import Decimal
from typing import Any

import pytest

from src.common.errors import ConflictError, NotFoundError, ValidationError
from src.pedidos.transitions import validate_transition


@pytest.mark.parametrize("current,target", [
    ("CREADO", "ACEPTADO"),
    ("CREADO", "CANCELADO"),
    ("ACEPTADO", "EN_PREPARACION"),
    ("ACEPTADO", "CANCELADO"),
    ("EN_PREPARACION", "DESPACHADO"),
    ("EN_PREPARACION", "CANCELADO"),
    ("DESPACHADO", "ENTREGADO"),
])
def test_allowed_order_transitions(current: str, target: str) -> None:
    validate_transition(current, target)


@pytest.mark.parametrize("current,target", [
    ("CREADO", "DESPACHADO"),
    ("ENTREGADO", "CANCELADO"),
    ("ENTREGADO", "ACEPTADO"),
    ("CANCELADO", "ACEPTADO"),
    ("CANCELADO", "CANCELADO"),
    ("DESPACHADO", "CANCELADO"),
])
def test_disallowed_order_transitions_conflict(current: str, target: str) -> None:
    with pytest.raises(ConflictError):
        validate_transition(current, target)


def test_unknown_order_state_is_bad_request() -> None:
    with pytest.raises(ValidationError):
        validate_transition("CREADO", "PENDIENTE")


def test_order_total_and_identity_are_server_derived(dynamodb_service: Any) -> None:
    service, products, _ = dynamodb_service
    products.put_item(Item={
        "id": "p-1",
        "nombre": "Té",
        "precio": Decimal("7500"),
        "stock": 5,
    })

    order = service.create_order(
        {"productos": [
            {"productoId": "p-1", "cantidad": 1},
            {"productoId": "p-1", "cantidad": 1},
        ]},
        customer_id="jwt-oid",
        customer_name="Nombre del token",
    )

    assert order["clienteId"] == "jwt-oid"
    assert order["clienteNombre"] == "Nombre del token"
    assert order["estado"] == "CREADO"
    assert order["total"] == Decimal("15000")
    assert order["productos"] == [{
        "productoId": "p-1",
        "nombre": "Té",
        "cantidad": 2,
        "precio": Decimal("7500"),
    }]


@pytest.mark.parametrize("payload", [
    {},
    {"productos": []},
    {"productos": [{"productoId": "p-1", "cantidad": 0}]},
    {"productos": [{"productoId": "p-1", "cantidad": True}]},
    {"productos": [{"productoId": "p-1", "cantidad": 1}], "total": 1},
])
def test_invalid_order_request_is_rejected(dynamodb_service: Any, payload: dict[str, Any]) -> None:
    service, _, _ = dynamodb_service

    with pytest.raises(ValidationError):
        service.create_order(payload, customer_id="customer-1", customer_name="")


def test_order_for_missing_product_is_404(dynamodb_service: Any) -> None:
    service, _, _ = dynamodb_service

    with pytest.raises(NotFoundError):
        service.create_order(
            {"productos": [{"productoId": "missing", "cantidad": 1}]},
            customer_id="customer-1",
            customer_name="",
        )



def test_orders_customer_index_returns_only_matching_customer(dynamodb_service: Any) -> None:
    service, _, orders = dynamodb_service
    for order_id, customer_id in (("o-1", "customer-1"), ("o-2", "customer-2")):
        orders.put_item(Item={"id": order_id, "clienteId": customer_id, "estado": "CREADO"})

    result = service.list_orders(customer_id="customer-1")

    assert [order["id"] for order in result] == ["o-1"]