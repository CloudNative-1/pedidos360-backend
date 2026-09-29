class AppError(Exception):
    status_code = 500
    error_code = "INTERNAL_SERVER_ERROR"

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class ValidationError(AppError):
    status_code = 400
    error_code = "VALIDATION_ERROR"


class UnauthorizedError(AppError):
    status_code = 401
    error_code = "UNAUTHORIZED"

    def __init__(self, message: str = "Se requiere una identidad autenticada."):
        super().__init__(message)


class ForbiddenError(AppError):
    status_code = 403
    error_code = "FORBIDDEN"

    def __init__(self, message: str = "Tu cuenta no tiene permiso para realizar esta operación."):
        super().__init__(message)


class NotFoundError(AppError):
    status_code = 404
    error_code = "NOT_FOUND"


class ConflictError(AppError):
    status_code = 409
    error_code = "CONFLICT"