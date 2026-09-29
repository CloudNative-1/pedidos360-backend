import json
from decimal import Decimal
from typing import Any

import pytest

from src.catalogo import handlers as catalog_handlers
from src.common.errors import NotFoundError, ValidationError


def _admin_event() -> dict[str, Any]:
    return {
        "requestContext": {
            "authorizer": {
                "jwt": {
                    "claims": {"sub": "admin-1", "roles": ["Admin"], "scp": "catalog.read catalog.write"},
                    "scopes": ["catalog.read", "catalog.write"],
                }
            }
        }
    }


def test_catalog_repository_and_service_crud(dynamodb_catalog: Any) -> None:
    service, table = dynamodb_catalog

    created = service.create_product({"nombre": "Té", "descripcion": "", "precio": 1200, "stock": 8})
    assert set(created) == {"id", "nombre", "descripcion", "precio", "stock"}
    assert created["descripcion"] == ""
    assert table.get_item(Key={"id": created["id"]})["Item"]["precio"] == Decimal("1200")
    assert service.list_products() == [created]
    assert service.get_product(created["id"]) == created

    updated = service.update_product(created["id"], {"stock": 4, "descripcion": "Té verde"})
    assert updated["stock"] == 4
    assert updated["descripcion"] == "Té verde"

    service.delete_product(created["id"])
    assert service.list_products() == []
    with pytest.raises(NotFoundError):
        service.get_product(created["id"])


@pytest.mark.parametrize("change", [
    {"nombre": ""},
    {"descripcion": None},
    {"precio": True},
    {"precio": -1},
    {"precio": float("nan")},
    {"stock": True},
    {"stock": -1},
    {"stock": 1.5},
    {"campoNoPermitido": "valor"},
])
def test_invalid_product_fields_are_rejected(dynamodb_catalog: Any, change: dict[str, Any]) -> None:
    service, _ = dynamodb_catalog
    payload: dict[str, Any] = {"nombre": "Té", "precio": 1200, "stock": 8}
    payload.update(change)

    with pytest.raises(ValidationError):
        service.create_product(payload)


def test_missing_required_product_fields_are_rejected(dynamodb_catalog: Any) -> None:
    service, _ = dynamodb_catalog

    with pytest.raises(ValidationError):
        service.create_product({"nombre": "Té", "stock": 8})
    with pytest.raises(ValidationError):
        service.update_product("missing", {})


def test_missing_product_maps_to_404(dynamodb_catalog: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    service, _ = dynamodb_catalog
    monkeypatch.setattr(catalog_handlers, "_service", service)
    event = {**_admin_event(), "pathParameters": {"id": "missing"}}

    result = catalog_handlers.obtener_producto(event, None)

    assert result["statusCode"] == 404
    assert json.loads(result["body"])["error"] == "NOT_FOUND"


def test_catalog_handlers_return_crud_statuses(dynamodb_catalog: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    service, _ = dynamodb_catalog
    monkeypatch.setattr(catalog_handlers, "_service", service)
    event = _admin_event()
    event["body"] = json.dumps({"nombre": "Té", "precio": 1200, "stock": 8})

    created_response = catalog_handlers.crear_producto(event, None)
    assert created_response["statusCode"] == 201
    product = json.loads(created_response["body"])
    product_id = product["id"]

    event["pathParameters"] = {"id": product_id}
    assert catalog_handlers.obtener_producto(event, None)["statusCode"] == 200
    event["body"] = json.dumps({"stock": 5})
    assert catalog_handlers.actualizar_producto(event, None)["statusCode"] == 200
    assert catalog_handlers.listar_catalogo(_admin_event(), None)["statusCode"] == 200
    assert catalog_handlers.eliminar_producto(event, None)["statusCode"] == 204
    assert catalog_handlers.obtener_producto(event, None)["statusCode"] == 404


def test_invalid_json_body_maps_to_400(dynamodb_catalog: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    service, _ = dynamodb_catalog
    monkeypatch.setattr(catalog_handlers, "_service", service)
    event = {**_admin_event(), "body": "{"}

    result = catalog_handlers.crear_producto(event, None)

    assert result["statusCode"] == 400
    assert json.loads(result["body"])["error"] == "VALIDATION_ERROR"