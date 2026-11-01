"""Request-level protections: security headers, request ids, logging and body-size limits."""

import logging
import re
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, HTTPException, Request, Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.errors import PayloadTooLarge
from app.handlers import error_response

log = logging.getLogger("utsav.http")

SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; script-src 'self' https://www.gstatic.com https://apis.google.com; "
        "connect-src 'self' https://*.googleapis.com; frame-src https://*.firebaseapp.com https://accounts.google.com; "
        "img-src 'self' data: blob:; style-src 'self' https://fonts.googleapis.com; "
        "font-src https://fonts.gstatic.com; "
        "frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    ),
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
}
_REQUEST_ID = re.compile(r"^[A-Za-z0-9-]{8,64}$")  # anything else is replaced, so logs can't be forged


class BodyLimitMiddleware:
    """Counts body bytes as they arrive, so chunked requests without Content-Length can't exceed the limit."""

    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        """Wraps `app`, allowing at most `max_bytes` of request body."""
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Passes the request on with a byte-counting receive; raises 413 once the limit is passed."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        received = 0

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    raise HTTPException(status_code=413, detail="Request body is too large")
            return message

        await self.app(scope, limited_receive, send)


def install_middleware(app: FastAPI, max_body_bytes: int) -> None:
    """Adds the body limit and the guard that sets security headers, request ids and logs."""
    # Added first so it sits inside the guard: routes read the counting receive directly.
    app.add_middleware(BodyLimitMiddleware, max_bytes=max_body_bytes)

    @app.middleware("http")
    async def guard(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        incoming = request.headers.get("x-request-id", "")
        request_id = incoming if _REQUEST_ID.match(incoming) else uuid.uuid4().hex
        started = time.perf_counter()
        length = request.headers.get("content-length", "")
        if length.isdigit() and int(length) > max_body_bytes:
            exc = PayloadTooLarge("Request body is too large")
            response: Response = error_response(exc.status, exc.code, exc.message)
        else:
            try:
                response = await call_next(request)
            except Exception:  # last resort: never leak details, always add the headers below
                log.exception("unhandled error", extra={"request_id": request_id, "path": request.url.path})
                response = error_response(500, "internal", "Something went wrong.")
        response.headers.update(SECURITY_HEADERS)
        response.headers["X-Request-ID"] = request_id
        log.info(
            "request",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "latency_ms": round((time.perf_counter() - started) * 1000, 1),
            },
        )
        return response
