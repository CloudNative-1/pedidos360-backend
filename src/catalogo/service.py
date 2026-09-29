import uuid
from datetime import datetime, timezone
from typing import Any

from src.catalogo.repository import CatalogRepository
from src.common.errors import NotFoundError, ValidationError
from src.common.validation import decimal_value, integer_value

_FIELDS = {"nombre", "descripcion", "precio", "stock"}


class CatalogService:
    def __init__(self, repository: CatalogRepository | Any | None = None) -> None:
        self.repository = repository or CatalogRepository()

    def list_products(self) -> list[dict[str, Any]]:
        return [self._public(item) for item in self.repository.list_products()]

    def get_product(self, product_id: str) -> dict[str, Any]:
        product = self.repository.get_product(product_id)
        if product is None:
            raise NotFoundError("No se encontró el producto solicitado.")
        return self._public(product)

    def create_product(self, payload: dict[str, Any]) -> dict[str, Any]:
        unknown = set(payload) - _FIELDS
        if unknown:
            raise ValidationError(f"Campos no permitidos: {', '.join(sorted(unknown))}.")
        product = self._validated_fields(payload, partial=False)
        product.setdefault("descripcion", "")
        now = _now()
        product.update({"id": str(uuid.uuid4()), "createdAt": now, "updatedAt": now})
        self.repository.create_product(product)
        return self._public(product)

    def update_product(self, product_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        unknown = set(payload) - _FIELDS
        if unknown:
            raise ValidationError(f"Campos no permitidos: {', '.join(sorted(unknown))}.")
        if not payload:
            raise ValidationError("Debe proporcionar al menos un campo para actualizar.")
        changes = self._validated_fields(payload, partial=True)
        changes["updatedAt"] = _now()
        product = self.repository.update_product(product_id, changes)
        if product is None:
            raise NotFoundError("No se encontró el producto solicitado.")
        return self._public(product)

    def delete_product(self, product_id: str) -> None:
        if not self.repository.delete_product(product_id):
            raise NotFoundError("No se encontró el producto solicitado.")

    @staticmethod
    def _validated_fields(payload: dict[str, Any], *, partial: bool) -> dict[str, Any]:
        if not partial and not {"nombre", "precio", "stock"}.issubset(payload):
            raise ValidationError("nombre, precio y stock son obligatorios.")
        result: dict[str, Any] = {}
        if "nombre" in payload:
            name = payload["nombre"]
            if not isinstance(name, str) or not name.strip():
                raise ValidationError("nombre no puede estar vacío.")
            result["nombre"] = name.strip()
        if "descripcion" in payload:
            description = payload["descripcion"]
            if not isinstance(description, str):
                raise ValidationError("descripcion debe ser texto.")
            result["descripcion"] = description
        if "precio" in payload:
            result["precio"] = decimal_value(payload["precio"], "precio")
        if "stock" in payload:
            result["stock"] = integer_value(payload["stock"], "stock", minimum=0)
        return result

    @staticmethod
    def _public(product: dict[str, Any]) -> dict[str, Any]:
        return {key: product[key] for key in ("id", "nombre", "descripcion", "precio", "stock") if key in product}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()