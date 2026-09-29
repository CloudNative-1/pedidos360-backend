import os
from typing import Any


class OrderRepository:
    def __init__(self) -> None:
        self.orders_table_name = os.environ.get("ORDERS_TABLE", "pedidos360-dev-pedidos")
        self.products_table_name = os.environ.get("PRODUCTS_TABLE", "pedidos360-dev-productos")
        self._resource: Any = None

    @property
    def resource(self) -> Any:
        if self._resource is None:
            import boto3

            self._resource = boto3.resource("dynamodb")
        return self._resource

    @property
    def orders(self) -> Any:
        return self.resource.Table(self.orders_table_name)

    @property
    def products(self) -> Any:
        return self.resource.Table(self.products_table_name)

    def get_product(self, product_id: str) -> dict[str, Any] | None:
        return self.products.get_item(Key={"id": product_id}).get("Item")

    def get_order(self, order_id: str) -> dict[str, Any] | None:
        return self.orders.get_item(Key={"id": order_id}).get("Item")

    def list_orders(self) -> list[dict[str, Any]]:
        return _scan_all(self.orders)

    def list_customer_orders(self, customer_id: str) -> list[dict[str, Any]]:
        query = {
            "IndexName": os.environ.get("ORDERS_CUSTOMER_INDEX", "clienteId-index"),
            "KeyConditionExpression": _key("clienteId").eq(customer_id),
        }
        items: list[dict[str, Any]] = []
        result = self.orders.query(**query)
        items.extend(result.get("Items", []))
        while result.get("LastEvaluatedKey"):
            result = self.orders.query(**query, ExclusiveStartKey=result["LastEvaluatedKey"])
            items.extend(result.get("Items", []))
        return items

    def create_order(self, order: dict[str, Any]) -> None:
        from botocore.exceptions import ClientError

        try:
            self.orders.put_item(Item=order, ConditionExpression="attribute_not_exists(id)")
        except ClientError as error:
            if error.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
                from src.common.errors import ConflictError

                raise ConflictError("Ya existe un pedido con ese identificador.") from error
            raise

    def update_order_state(self, order: dict[str, Any], target_state: str, updated_at: str) -> dict[str, Any]:
        transactions = []
        if target_state == "ACEPTADO":
            for product in order["productos"]:
                transactions.append({"Update": {
                    "TableName": self.products_table_name,
                    "Key": {"id": product["productoId"]},
                    "UpdateExpression": "SET #stock = #stock - :quantity",
                    "ConditionExpression": "attribute_exists(id) AND #stock >= :quantity",
                    "ExpressionAttributeNames": {"#stock": "stock"},
                    "ExpressionAttributeValues": {":quantity": product["cantidad"]},
                }})
        elif target_state == "CANCELADO" and order["estado"] in {"ACEPTADO", "EN_PREPARACION"}:
            for product in order["productos"]:
                transactions.append({"Update": {
                    "TableName": self.products_table_name,
                    "Key": {"id": product["productoId"]},
                    "UpdateExpression": "SET #stock = #stock + :quantity",
                    "ConditionExpression": "attribute_exists(id)",
                    "ExpressionAttributeNames": {"#stock": "stock"},
                    "ExpressionAttributeValues": {":quantity": product["cantidad"]},
                }})
        transactions.append({"Update": {
            "TableName": self.orders_table_name,
            "Key": {"id": order["id"]},
            "UpdateExpression": "SET #estado = :target, #updated = :updated",
            "ConditionExpression": "#estado = :current",
            "ExpressionAttributeNames": {"#estado": "estado", "#updated": "fechaActualizacion"},
            "ExpressionAttributeValues": {
                ":target": target_state,
                ":current": order["estado"],
                ":updated": updated_at,
            },
        }})
        self._transact(self.orders.meta.client, transactions, "No hay stock suficiente o el pedido cambió durante la operación.")
        updated = dict(order)
        updated.update({"estado": target_state, "fechaActualizacion": updated_at})
        return updated

    @staticmethod
    def _transact(client: Any, items: list[dict[str, Any]], message: str) -> None:
        from botocore.exceptions import ClientError
        from src.common.errors import ConflictError

        try:
            client.transact_write_items(TransactItems=items)
        except ClientError as error:
            if error.response.get("Error", {}).get("Code") in {"TransactionCanceledException", "ConditionalCheckFailedException"}:
                raise ConflictError(message) from error
            raise


def _key(name: str) -> Any:
    from boto3.dynamodb.conditions import Key

    return Key(name)


def _scan_all(table: Any) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    result = table.scan()
    items.extend(result.get("Items", []))
    while result.get("LastEvaluatedKey"):
        result = table.scan(ExclusiveStartKey=result["LastEvaluatedKey"])
        items.extend(result.get("Items", []))
    return items
