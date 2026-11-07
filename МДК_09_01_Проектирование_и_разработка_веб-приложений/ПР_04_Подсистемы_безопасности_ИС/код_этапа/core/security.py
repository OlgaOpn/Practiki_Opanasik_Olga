import base64
import hashlib
import hmac
import secrets
from functools import wraps

from starlette.exceptions import HTTPException
from starlette.responses import RedirectResponse

from . import config


class PasswordHasher:
    N, R, P = 2 ** 14, 8, 1

    def hash(self, password: str) -> str:
        salt = secrets.token_bytes(16)
        digest = hashlib.scrypt(password.encode(), salt=salt, n=self.N, r=self.R, p=self.P)
        b64 = lambda b: base64.b64encode(b).decode()
        return f"scrypt${self.N}${self.R}${self.P}${b64(salt)}${b64(digest)}"

    def verify(self, password: str, stored: str) -> bool:
        try:
            _, n, r, p, salt, digest = stored.split("$")
            check = hashlib.scrypt(password.encode(), salt=base64.b64decode(salt), n=int(n), r=int(r), p=int(p))
            return hmac.compare_digest(check, base64.b64decode(digest))
        except (ValueError, TypeError):
            return False


hasher = PasswordHasher()


def csrf_token(request) -> str:
    if "csrf" not in request.session:
        request.session["csrf"] = secrets.token_urlsafe(32)
    return request.session["csrf"]


def csrf_valid(request, form) -> bool:
    sent = form.get("csrf_token", "")
    return bool(sent) and hmac.compare_digest(sent, request.session.get("csrf", ""))


def login_required(*roles):
    def decorator(handler):
        @wraps(handler)
        async def wrapper(request):
            user = request.state.user
            if user is None:
                request.session["flash"] = [("info", "Войдите, чтобы продолжить")]
                return RedirectResponse(f"/login?next={request.url.path}", status_code=303)
            if roles and user["role"] not in roles:
                raise HTTPException(403, "Недостаточно прав")
            return await handler(request)
        return wrapper
    return decorator


class LoginThrottle:
    def __init__(self, db):
        self.db = db

    def _since(self) -> str:
        if self.db.dialect == "mysql":
            return f"NOW() - INTERVAL {config.LOGIN_WINDOW_MIN} MINUTE"
        return f"datetime('now', '-{config.LOGIN_WINDOW_MIN} minutes')"

    def blocked(self, login: str) -> bool:
        row = self.db.one(f"SELECT COUNT(*) AS n FROM login_failures WHERE login = ? AND created_at > {self._since()}",
                          (login,))
        return row["n"] >= config.LOGIN_LIMIT

    def fail(self, login: str, ip: str) -> None:
        self.db.run("INSERT INTO login_failures (login, ip) VALUES (?, ?)", (login[:24], ip))

    def reset(self, login: str) -> None:
        self.db.run("DELETE FROM login_failures WHERE login = ?", (login,))
