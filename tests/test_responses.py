import json

import pytest

from src.common.errors import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)
from src.common.responses import run_handler


@pytest.mark.parametrize(("error", "status", "code"), [
    (ValidationError("invalid"), 400, "VALIDATION_ERROR"),
    (UnauthorizedError(), 401, "UNAUTHORIZED"),
    (ForbiddenError(), 403, "FORBIDDEN"),
    (NotFoundError("missing"), 404, "NOT_FOUND"),
    (ConflictError("changed"), 409, "CONFLICT"),
])
def test_domain_errors_have_consistent_http_responses(error: Exception, status: int, code: str) -> None:
    def action() -> dict:
        raise error

    result = run_handler({}, "test", action)

    assert result["statusCode"] == status
    assert set(json.loads(result["body"])) == {"error", "message"}
    assert json.loads(result["body"])["error"] == code


def test_unhandled_error_returns_generic_500_without_stack_trace() -> None:
    def action() -> dict:
        raise RuntimeError("internal detail")

    result = run_handler({}, "test", action)
    body = json.loads(result["body"])

    assert result["statusCode"] == 500
    assert body == {"error": "INTERNAL_SERVER_ERROR", "message": "Ocurrió un error interno."}
    assert "RuntimeError" not in result["body"]