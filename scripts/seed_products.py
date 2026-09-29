#!/usr/bin/env python3
"""Seed de productos de demostración para Pedidos360.

Inserta los 6 productos demo (IDs estables) directamente en DynamoDB
``backend-pedidos360-dev-productos``. Es idempotente: los productos que ya
existen se omiten y nunca se sobrescriben salvo que se indique
explicitamente con ``--force``.

Uso:
    python scripts/seed_products.py                 # inserta solo los que faltan
    python scripts/seed_products.py --dry-run       # muestra qué haría sin escribir
    python scripts/seed_products.py --force --yes   # sobrescribe los existentes
    python scripts/seed_products.py --profile pedidos360

Dependencias: boto3, botocore (requirements-dev.txt).
Credenciales: perfil AWS Academy / VocLabs ``pedidos360`` (AWS_PROFILE).
No almacena ni imprime credenciales.

El frontend (vista Cliente / "Comprar") usa una fuente de demostración con
estos mismos IDs, por lo que los pedidos creados desde la UI apuntan a
productos que sí existen en DynamoDB.
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import Any

PRODUCTS: list[dict[str, Any]] = [
    {
        "id": "prod-teclado-001",
        "nombre": "Teclado Mecánico Compacto",
        "descripcion": "Teclado compacto para trabajo y estudio.",
        "precio": 39990,
        "stock": 20,
    },
    {
        "id": "prod-mouse-002",
        "nombre": "Mouse Inalámbrico",
        "descripcion": "Mouse ergonómico para uso diario.",
        "precio": 18990,
        "stock": 30,
    },
    {
        "id": "prod-audifonos-003",
        "nombre": "Audífonos USB",
        "descripcion": "Audífonos con micrófono integrado.",
        "precio": 24990,
        "stock": 15,
    },
    {
        "id": "prod-webcam-004",
        "nombre": "Webcam Full HD",
        "descripcion": "Cámara para reuniones y videollamadas.",
        "precio": 32990,
        "stock": 12,
    },
    {
        "id": "prod-hub-005",
        "nombre": "Hub USB-C",
        "descripcion": "Adaptador multipuerto para notebook.",
        "precio": 28990,
        "stock": 18,
    },
    {
        "id": "prod-soporte-006",
        "nombre": "Soporte para Notebook",
        "descripcion": "Soporte ajustable para escritorio.",
        "precio": 21990,
        "stock": 25,
    },
]


def _item_key(product_id: str) -> dict[str, str]:
    return {"id": product_id}


def _insert(table: Any, product: dict[str, Any]) -> None:
    from botocore.exceptions import ClientError

    item = dict(product)
    item.setdefault("createdAt", "")
    item["updatedAt"] = ""
    try:
        table.put_item(Item=item, ConditionExpression="attribute_not_exists(id)")
    except ClientError as error:
        code = error.response.get("Error", {}).get("Code")
        if code == "ConditionalCheckFailedException":
            return  # ya existe: se omite (nunca se pisa sin --force)
        raise


def _overwrite(table: Any, product: dict[str, Any]) -> None:
    item = dict(product)
    item["updatedAt"] = ""
    table.put_item(Item=item)


def run(args: argparse.Namespace) -> int:
    table_name = args.table or os.environ.get("PRODUCTS_TABLE", "backend-pedidos360-dev-productos")
    if args.profile:
        os.environ["AWS_PROFILE"] = args.profile
    elif not os.environ.get("AWS_PROFILE") and not os.environ.get("AWS_ACCESS_KEY_ID"):
        os.environ["AWS_PROFILE"] = "pedidos360"

    import boto3

    table = boto3.resource("dynamodb").Table(table_name)

    inserted: list[str] = []
    overwritten: list[str] = []
    skipped: list[str] = []

    for product in PRODUCTS:
        existing = table.get_item(Key=_item_key(product["id"])).get("Item")
        if existing is None:
            if args.dry_run:
                print(f"[dry-run] insertaría: {product['id']} — {product['nombre']}")
                continue
            _insert(table, product)
            inserted.append(product["id"])
            print(f"[ok] insertado: {product['id']} — {product['nombre']}")
        elif args.force:
            if args.dry_run:
                print(f"[dry-run] sobrescribiría: {product['id']} — {product['nombre']}")
                continue
            _overwrite(table, product)
            overwritten.append(product["id"])
            print(f"[ok] sobrescrito: {product['id']} — {product['nombre']}")
        else:
            skipped.append(product["id"])
            print(f"[omitido] ya existe: {product['id']} (use --force para sobrescribir)")

    print(
        f"\nTabla: {table_name}\n"
        f"Insertados: {len(inserted)} | Sobrescritos: {len(overwritten)} | Omitidos: {len(skipped)}"
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scripts/seed_products.py",
        description="Seed de productos de demostración en DynamoDB (Pedidos360).",
    )
    parser.add_argument("--profile", help="Perfil AWS a usar (default: pedidos360).")
    parser.add_argument("--table", help="Nombre de la tabla DynamoDB (default: PRODUCTS_TABLE o backend-pedidos360-dev-productos).")
    parser.add_argument("--force", action="store_true", help="Sobrescribir productos existentes.")
    parser.add_argument("--yes", action="store_true", help="Confirmar --force sin preguntar.")
    parser.add_argument("--dry-run", action="store_true", help="Mostrar qué haría sin escribir.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.force and not args.yes:
        answer = input(
            "--force sobrescribirá los productos demo existentes. ¿Continuar? [s/N] "
        ).strip().lower()
        if answer not in {"s", "si", "sí", "y", "yes"}:
            print("Operación cancelada.")
            return 1
    return run(args)


if __name__ == "__main__":
    sys.exit(main())