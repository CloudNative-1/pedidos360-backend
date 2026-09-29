import os
from typing import Any


class CatalogRepository:
    def __init__(self) -> None:
        self.table_name = os.environ.get("PRODUCTS_TABLE", "pedidos360-dev-productos")
        self._table: Any = None

    @property
    def table(self) -> Any:
        if self._table is None:
            import boto3

            self._table = boto3.resource("dynamodb").Table(self.table_name)
        return self._table

    def list_products(self) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        result = self.table.scan()
        items.extend(result.get("Items", []))
        while result.get("LastEvaluatedKey"):
            result = self.table.scan(ExclusiveStartKey=result["LastEvaluatedKey"])
            items.extend(result.get("Items", []))
        return items

    def get_product(self, product_id: str) -> dict[str, Any] | None:
        return self.table.get_item(Key={"id": product_id}).get("Item")

    def create_product(self, product: dict[str, Any]) -> None:
        from botocore.exceptions import ClientError

        try:
            self.table.put_item(Item=product, ConditionExpression="attribute_not_exists(id)")
        except ClientError as error:
            if error.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
                from src.common.errors import ConflictError

                raise ConflictError("Ya existe un producto con ese identificador.") from error
            raise

    def update_product(self, product_id: str, changes: dict[str, Any]) -> dict[str, Any] | None:
        names = {f"#{key}": key for key in changes}
        values = {f":{key}": value for key, value in changes.items()}
        update = ", ".join(f"#{key} = :{key}" for key in changes)
        try:
            result = self.table.update_item(
                Key={"id": product_id},
                UpdateExpression=f"SET {update}",
                ExpressionAttributeNames=names,
                ExpressionAttributeValues=values,
                ConditionExpression="attribute_exists(id)",
                ReturnValues="ALL_NEW",
            )
        except Exception as error:
            if _conditional_failure(error):
                return None
            raise
        return result.get("Attributes")

    def delete_product(self, product_id: str) -> bool:
        try:
            self.table.delete_item(Key={"id": product_id}, ConditionExpression="attribute_exists(id)")
        except Exception as error:
            if _conditional_failure(error):
                return False
            raise
        return True


def _conditional_failure(error: Exception) -> bool:
    response = getattr(error, "response", {})
    code = response.get("Error", {}).get("Code")
    if code == "ConditionalCheckFailedException":
        return True
    reasons = response.get("CancellationReasons", [])
    return any(reason.get("Code") == "ConditionalCheckFailed" for reason in reasons)