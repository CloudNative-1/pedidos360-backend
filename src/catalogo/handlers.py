from typing import Any

from src.auth.authorization import require_access
from src.catalogo.service import CatalogService
from src.common.responses import response, run_handler
from src.common.validation import parse_json_body

_service = CatalogService()
_CATALOG_READ_ROLES = {"Admin", "Operador"}
_CATALOG_WRITE_ROLES = {"Admin"}


def listar_catalogo(event: dict[str, Any], context: Any) -> dict[str, Any]:
    return run_handler(event, "GET /catalogo", lambda: _list(event))


def obtener_producto(event: dict[str, Any], context: Any) -> dict[str, Any]:
    return run_handler(event, "GET /catalogo/{id}", lambda: _get(event))


def crear_producto(event: dict[str, Any], context: Any) -> dict[str, Any]:
    return run_handler(event, "POST /catalogo", lambda: _create(event))


def actualizar_producto(event: dict[str, Any], context: Any) -> dict[str, Any]:
    return run_handler(event, "PUT /catalogo/{id}", lambda: _update(event))


def eliminar_producto(event: dict[str, Any], context: Any) -> dict[str, Any]:
    return run_handler(event, "DELETE /catalogo/{id}", lambda: _delete(event))


def _list(event: dict[str, Any]) -> dict[str, Any]:
    require_access(event, _CATALOG_READ_ROLES, "catalog.read")
    return response(200, _service.list_products())


def _get(event: dict[str, Any]) -> dict[str, Any]:
    require_access(event, _CATALOG_READ_ROLES, "catalog.read")
    return response(200, _service.get_product(_path_id(event)))


def _create(event: dict[str, Any]) -> dict[str, Any]:
    require_access(event, _CATALOG_WRITE_ROLES, "catalog.write")
    return response(201, _service.create_product(parse_json_body(event)))


def _update(event: dict[str, Any]) -> dict[str, Any]:
    require_access(event, _CATALOG_WRITE_ROLES, "catalog.write")
    return response(200, _service.update_product(_path_id(event), parse_json_body(event)))


def _delete(event: dict[str, Any]) -> dict[str, Any]:
    require_access(event, _CATALOG_WRITE_ROLES, "catalog.write")
    _service.delete_product(_path_id(event))
    return response(204)


def _path_id(event: dict[str, Any]) -> str:
    return str((event.get("pathParameters") or {}).get("id") or "")