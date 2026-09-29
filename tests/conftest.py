from typing import Any

import boto3
import pytest
from moto import mock_aws

from src.catalogo.repository import CatalogRepository
from src.catalogo.service import CatalogService
from src.pedidos.repository import OrderRepository
from src.pedidos.service import OrderService


@pytest.fixture
def dynamodb_tables(monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("PRODUCTS_TABLE", "test-productos")
    monkeypatch.setenv("ORDERS_TABLE", "test-pedidos")
    monkeypatch.setenv("ORDERS_CUSTOMER_INDEX", "clienteId-index")

    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        products = dynamodb.create_table(
            TableName="test-productos",
            KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        orders = dynamodb.create_table(
            TableName="test-pedidos",
            KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
            AttributeDefinitions=[
                {"AttributeName": "id", "AttributeType": "S"},
                {"AttributeName": "clienteId", "AttributeType": "S"},
            ],
            GlobalSecondaryIndexes=[{
                "IndexName": "clienteId-index",
                "KeySchema": [{"AttributeName": "clienteId", "KeyType": "HASH"}],
                "Projection": {"ProjectionType": "ALL"},
            }],
            BillingMode="PAY_PER_REQUEST",
        )
        yield products, orders


@pytest.fixture
def dynamodb_service(dynamodb_tables: Any) -> tuple[OrderService, Any, Any]:
    products, orders = dynamodb_tables
    return OrderService(OrderRepository()), products, orders


@pytest.fixture
def dynamodb_catalog(dynamodb_tables: Any) -> tuple[CatalogService, Any]:
    products, _ = dynamodb_tables
    return CatalogService(CatalogRepository()), products