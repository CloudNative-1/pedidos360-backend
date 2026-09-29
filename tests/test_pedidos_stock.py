from decimal import Decimal
from typing import Any

import pytest

from src.common.errors import ConflictError
from src.pedidos.service import OrderService


def _put_product(products: Any, product_id: str = "p-1", stock: int = 5) -> None:
    products.put_item(Item={
        "id": product_id,
        "nombre": f"Producto {product_id}",
        "precio": Decimal("7500"),
        "stock": stock,
    })


def _create_order(service: OrderService, product_ids: list[str] | None = None) -> dict[str, Any]:
    ids = product_ids or ["p-1"]
    return service.create_order(
        {"productos": [{"productoId": product_id, "cantidad": 2} for product_id in ids]},
        customer_id="customer-1",
        customer_name="Cliente de prueba",
    )


def _stock(products: Any, product_id: str = "p-1") -> int:
    return products.get_item(Key={"id": product_id})["Item"]["stock"]


def test_create_keeps_stock_and_acceptance_decrements_it(dynamodb_service: Any) -> None:
    service, products, _ = dynamodb_service
    _put_product(products)

    order = _create_order(service)
    assert order["estado"] == "CREADO"
    assert _stock(products) == 5

    accepted = service.update_state(order["id"], "ACEPTADO")
    assert accepted["estado"] == "ACEPTADO"
    assert _stock(products) == 3


def test_acceptance_conflict_leaves_order_and_all_stock_unchanged(dynamodb_service: Any) -> None:
    service, products, _ = dynamodb_service
    _put_product(products, "p-1", stock=5)
    _put_product(products, "p-2", stock=5)
    order = _create_order(service, ["p-1", "p-2"])
    products.update_item(
        Key={"id": "p-2"},
        UpdateExpression="SET #stock = :stock",
        ExpressionAttributeNames={"#stock": "stock"},
        ExpressionAttributeValues={":stock": 1},
    )

    with pytest.raises(ConflictError):
        service.update_state(order["id"], "ACEPTADO")

    assert _stock(products, "p-1") == 5
    assert _stock(products, "p-2") == 1
    assert service.get_order(order["id"])["estado"] == "CREADO"


def test_zero_stock_order_is_created_but_cannot_be_accepted(dynamodb_service: Any) -> None:
    service, products, _ = dynamodb_service
    _put_product(products, stock=0)

    order = _create_order(service)
    assert order["estado"] == "CREADO"
    assert _stock(products) == 0

    with pytest.raises(ConflictError):
        service.update_state(order["id"], "ACEPTADO")

    assert _stock(products) == 0
    assert service.get_order(order["id"])["estado"] == "CREADO"


def test_cancel_created_order_does_not_restore_unreserved_stock(dynamodb_service: Any) -> None:
    service, products, _ = dynamodb_service
    _put_product(products)

    order = _create_order(service)
    assert _stock(products) == 5
    cancelled = service.update_state(order["id"], "CANCELADO")

    assert cancelled["estado"] == "CANCELADO"
    assert _stock(products) == 5


@pytest.mark.parametrize("next_state", ["ACEPTADO", "EN_PREPARACION"])
def test_cancel_after_acceptance_restores_stock_once(dynamodb_service: Any, next_state: str) -> None:
    service, products, _ = dynamodb_service
    _put_product(products)

    order = _create_order(service)
    service.update_state(order["id"], "ACEPTADO")
    assert _stock(products) == 3
    if next_state == "EN_PREPARACION":
        service.update_state(order["id"], next_state)

    cancelled = service.update_state(order["id"], "CANCELADO")

    assert cancelled["estado"] == "CANCELADO"
    assert _stock(products) == 5
    with pytest.raises(ConflictError):
        service.update_state(order["id"], "CANCELADO")
    assert _stock(products) == 5
