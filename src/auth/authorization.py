from typing import Any, Iterable

from src.auth.claims import Principal, get_principal
from src.common.errors import ForbiddenError, UnauthorizedError


def require_authenticated(event: dict[str, Any]) -> Principal:
    principal = get_principal(event)
    if principal is None:
        raise UnauthorizedError()
    return principal


def require_roles(event: dict[str, Any], allowed_roles: Iterable[str]) -> Principal:
    principal = require_authenticated(event)
    if not principal.roles.intersection(allowed_roles):
        raise ForbiddenError("Tu cuenta no tiene un rol autorizado para esta operación.")
    return principal


def require_scopes(event: dict[str, Any], required_scopes: Iterable[str]) -> Principal:
    principal = require_authenticated(event)
    missing = set(required_scopes) - principal.scopes
    if missing:
        raise ForbiddenError("Tu token no incluye los permisos necesarios para esta operación.")
    return principal


def require_access(event: dict[str, Any], allowed_roles: Iterable[str], required_scope: str) -> Principal:
    principal = require_roles(event, allowed_roles)
    if required_scope not in principal.scopes:
        raise ForbiddenError("Tu token no incluye los permisos necesarios para esta operación.")
    return principal