from decimal import Decimal
from typing import TypedDict


class Producto(TypedDict):
    id: str
    nombre: str
    descripcion: str
    precio: Decimal
    stock: int