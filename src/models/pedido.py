from decimal import Decimal
from typing import TypedDict


class ProductoPedido(TypedDict):
    productoId: str
    nombre: str
    cantidad: int
    precio: Decimal


class Pedido(TypedDict):
    id: str
    clienteId: str
    clienteNombre: str
    estado: str
    fechaCreacion: str
    fechaActualizacion: str
    total: Decimal
    productos: list[ProductoPedido]