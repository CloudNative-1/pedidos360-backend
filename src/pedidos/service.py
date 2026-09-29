import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from src.common.errors import NotFoundError, ValidationError
from src.common.validation import integer_value
from src.pedidos.repository import OrderRepository
from src.pedidos.transitions import validate_transition


class OrderService:
    def __init__(self, repository: OrderRepository | Any | None = None) -> None:
        self.repository = repository or OrderRepository()

    def list_orders(self, *, customer_id: str | None = None) -> list[dict[str, Any]]:
        orders = self.repository.list_orders() if customer_id is None else self.repository.list_customer_orders(customer_id)
        return [self._public(order) for order in orders]

    def get_order(self, order_id: str) -> dict[str, Any]:
        order = self.repository.get_order(order_id)
        if order is None:
            raise NotFoundError("No se encontró el pedido solicitado.")
        return self._public(order)

    def create_order(self, payload: dict[str, Any], *, customer_id: str, customer_name: str) -> dict[str, Any]:
        if set(payload) != {"productos"}:
            raise ValidationError("El cuerpo debe contener únicamente productos.")
        requested = payload["productos"]
        if not isinstance(requested, list) or not requested:
            raise ValidationError("Debe incluir al menos un producto.")
        quantities: dict[str, int] = {}
        for line in requested:
            if not isinstance(line, dict) or set(line) != {"productoId", "cantidad"}:
                raise ValidationError("Cada producto debe contener productoId y cantidad.")
            product_id = line["productoId"]
            if not isinstance(product_id, str) or not product_id.strip():
                raise ValidationError("productoId es obligatorio.")
            quantity = integer_value(line["cantidad"], "cantidad", minimum=1)
            quantities[product_id.strip()] = quantities.get(product_id.strip(), 0) + quantity
        if len(quantities) > 99:
            raise ValidationError("Un pedido no puede incluir más de 99 productos distintos.")

        products = []
        total = Decimal("0")
        for product_id, quantity in quantities.items():
            product = self.repository.get_product(product_id)
            if product is None:
                raise NotFoundError(f"No se encontró el producto {product_id}.")
            price = Decimal(str(product["precio"]))
            line_total = price * quantity
            total += line_total
            products.append({
                "productoId": product_id,
                "nombre": product["nombre"],
                "cantidad": quantity,
                "precio": price,
            })

        now = _now()
        order = {
            "id": str(uuid.uuid4()),
            "clienteId": customer_id,
            "clienteNombre": customer_name,
            "estado": "CREADO",
            "fechaCreacion": now,
            "fechaActualizacion": now,
            "total": total,
            "productos": products,
        }
        self.repository.create_order(order)
        return self._public(order)

    def update_state(self, order_id: str, target_state: str) -> dict[str, Any]:
        if not isinstance(target_state, str):
            raise ValidationError("estado es obligatorio y debe ser texto.")
        order = self.repository.get_order(order_id)
        if order is None:
            raise NotFoundError("No se encontró el pedido solicitado.")
        validate_transition(order["estado"], target_state)
        updated = self.repository.update_order_state(order, target_state, _now())
        return self._public(updated)

    @staticmethod
    def _public(order: dict[str, Any]) -> dict[str, Any]:
        keys = ("id", "clienteId", "clienteNombre", "estado", "fechaCreacion", "fechaActualizacion", "total", "productos")
        return {key: order[key] for key in keys if key in order}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()