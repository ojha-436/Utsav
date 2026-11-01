"""Application errors. Each maps to one HTTP status and a stable error code."""


class AppError(Exception):
    status: int = 500
    code: str = "internal"

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class InvalidInput(AppError):
    status, code = 422, "invalid_input"


class Unauthorized(AppError):
    status, code = 401, "unauthorized"


class NotFound(AppError):
    status, code = 404, "not_found"


class PayloadTooLarge(AppError):
    status, code = 413, "payload_too_large"


class UnsupportedMedia(AppError):
    status, code = 415, "unsupported_media_type"


class RateLimited(AppError):
    status, code = 429, "rate_limited"


class AIUnavailable(AppError):
    status, code = 502, "ai_unavailable"
