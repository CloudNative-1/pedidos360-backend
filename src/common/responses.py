import json
import logging
from typing import Any, Callable

from src.common.errors import AppError
from src.common.serialization import json_default

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def response(status_code: int, body: Any = None) -> dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json; charset=utf-8"},
        "body": "" if status_code == 204 else json.dumps(body, ensure_ascii=False, default=json_default),
    }


def run_handler(event: dict[str, Any], operation: str, action: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    request_id = ((event.get("requestContext") or {}).get("requestId"))
    logger.info("operation=%s request_id=%s", operation, request_id or "-")
    try:
        return action()
    except AppError as error:
        return response(error.status_code, {"error": error.error_code, "message": error.message})
    except Exception:
        logger.exception("operation=%s request_id=%s failed", operation, request_id or "-")
        return response(500, {"error": "INTERNAL_SERVER_ERROR", "message": "Ocurrió un error interno."})