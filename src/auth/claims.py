import json
from dataclasses import dataclass
from typing import Any


def _strings(value: Any) -> set[str]:
    if isinstance(value, (list, tuple, set)):
        return {item.strip() for entry in value for item in _strings(entry) if item.strip()}
    if not isinstance(value, str):
        return set()
    value = value.strip()
    if not value:
        return set()
    try:
        decoded = json.loads(value)
    except (json.JSONDecodeError, TypeError):
        decoded = None
    if isinstance(decoded, (list, tuple, set)):
        return _strings(decoded)
    if isinstance(decoded, str) and decoded != value:
        return _strings(decoded)
    return {part for part in value.replace(",", " ").split() if part}


@dataclass(frozen=True)
class Principal:
    claims: dict[str, Any]
    roles: frozenset[str]
    scopes: frozenset[str]
    subject: str
    customer_id: str
    name: str


def get_claims(event: dict[str, Any]) -> dict[str, Any]:
    request_context = event.get("requestContext") or {}
    authorizer = request_context.get("authorizer") or {}
    jwt = authorizer.get("jwt") or {}
    claims = jwt.get("claims")
    return claims if isinstance(claims, dict) else {}


def get_principal(event: dict[str, Any]) -> Principal | None:
    claims = get_claims(event)
    subject = claims.get("sub")
    customer_id = claims.get("oid") or subject
    if not isinstance(subject, str) or not subject.strip() or not isinstance(customer_id, str):
        return None
    roles = _strings(claims.get("roles"))
    scopes = _strings(claims.get("scope")) | _strings(claims.get("scp"))
    authorizer = ((event.get("requestContext") or {}).get("authorizer") or {})
    jwt_scopes = ((authorizer.get("jwt") or {}).get("scopes"))
    scopes |= _strings(jwt_scopes)
    name = claims.get("name") or claims.get("preferred_username") or ""
    return Principal(claims, frozenset(roles), frozenset(scopes), subject, customer_id, str(name))