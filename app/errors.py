"""Application errors. Each maps to one HTTP status and a stable error code."""


class AppError(Exception):
    """Base class for errors the API reports to the client. Subclasses set `status` and `code`."""

    status: int = 500
    code: str = "internal"

    def __init__(self, message: str) -> None:
        """Stores a user-readable message, which is safe to show to the client."""
        super().__init__(message)
        self.message = message


class InvalidInput(AppError):
    """422: the request is well-formed but not allowed (e.g. an event date in the past)."""

    status, code = 422, "invalid_input"


class Unauthorized(AppError):
    """401: sign-in is required, or the token is invalid."""

    status, code = 401, "unauthorized"


class NotFound(AppError):
    """404: the item doesn't exist for this user."""

    status, code = 404, "not_found"


class Conflict(AppError):
    """409: too many simultaneous changes; the client should retry."""

    status, code = 409, "conflict"


class PayloadTooLarge(AppError):
    """413: the request body or image is over the size limit."""

    status, code = 413, "payload_too_large"


class UnsupportedMedia(AppError):
    """415: the upload isn't a JPEG, PNG or WebP image."""

    status, code = 415, "unsupported_media_type"


class RateLimited(AppError):
    """429: too many requests in the current window."""

    status, code = 429, "rate_limited"


class AIUnavailable(AppError):
    """502: Gemini failed or returned something unusable."""

    status, code = 502, "ai_unavailable"
