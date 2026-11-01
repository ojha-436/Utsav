"""Firebase ID-token verification. The uid always comes from the verified token."""
import threading
from collections.abc import Callable

from fastapi import Depends, Header, Request

from app.errors import Unauthorized

_init_lock = threading.Lock()


def firebase_verifier(project_id: str) -> Callable[[str], str]:
    def verify(token: str) -> str:
        import firebase_admin
        from firebase_admin import auth

        with _init_lock:
            try:
                firebase_admin.get_app()
            except ValueError:
                firebase_admin.initialize_app(options={"projectId": project_id})
        try:
            return auth.verify_id_token(token)["uid"]
        except Exception as exc:  # any verification failure is a 401, never a 500
            raise Unauthorized("Invalid or expired sign-in") from exc

    return verify


def optional_user(request: Request, authorization: str | None = Header(default=None)) -> str | None:
    """None for guests. A present but bad token is a 401, never a silent guest."""
    if authorization is None:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise Unauthorized("Invalid sign-in token")
    return request.app.state.verify_token(token.strip())


def require_user(uid: str | None = Depends(optional_user)) -> str:
    if uid is None:
        raise Unauthorized("Sign in required")
    return uid
