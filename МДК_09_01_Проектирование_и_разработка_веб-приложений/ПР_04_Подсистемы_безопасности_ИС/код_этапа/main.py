"""«Добрый город» — портал волонтёрских акций.

Запуск:  pip install -r requirements.txt  &&  python main.py   →  http://127.0.0.1:8000
Координатор по умолчанию: coordinator / Dobro2026!
"""
import os
from datetime import date

import uvicorn
from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

from core import config
from core.db import Database
from core.forms import TASKS, RegistrationForm, SignupForm, validate
from core.repositories import ActionRepository, MemberRepository, SignupRepository
from core.security import LoginThrottle, csrf_token, csrf_valid, hasher, login_required

db = Database(config.DATABASE_URL)
members, actions, signups = MemberRepository(db), ActionRepository(db), SignupRepository(db)
throttle = LoginThrottle(db)
templates = Jinja2Templates(directory=config.BASE_DIR / "templates")


def render(request, name, status_code=200, **ctx):
    flashes = request.session.pop("flash", [])
    ctx.update(request=request, user=request.state.user, csrf=csrf_token(request), flashes=flashes, today=date.today().isoformat())
    return templates.TemplateResponse(request, name, ctx, status_code=status_code)


def flash(request, kind, text):
    request.session.setdefault("flash", []).append((kind, text))


def go(url):
    return RedirectResponse(url, status_code=303)


async def checked_form(request):
    """Читает форму и проверяет CSRF-токен. Без верного токена — ошибка 403."""
    form = await request.form()
    if not csrf_valid(request, form):
        raise HTTPException(403, "Форма устарела. Обновите страницу и отправьте её снова.")
    return form


# ================= гость =================
async def home(request):
    return render(request, "index.html", actions=actions.upcoming())


async def register(request):
    data, errors = {}, {}
    if request.method == "POST":
        data = dict(await checked_form(request))
        form, errors = validate(RegistrationForm, data)
        if form:
            if members.by_login(form.login):
                errors["login"] = "Этот логин уже занят"
            if members.email_taken(form.email):
                errors["email"] = "На эту почту уже зарегистрирован аккаунт"
        if not errors:
            members.create(form, hasher.hash(form.password))
            flash(request, "ok", "Аккаунт создан. Войдите, чтобы записаться на акцию.")
            return go("/login")
    data.pop("password", None), data.pop("password2", None)   # пароль обратно в форму не возвращаем
    return render(request, "register.html", data=data, errors=errors, status_code=400 if errors else 200)


async def login(request):
    error, login_value = None, ""
    if request.method == "POST":
        form = await checked_form(request)
        login_value = form.get("login", "").strip()
        ip = request.client.host if request.client else "-"
        if throttle.blocked(login_value):
            error = f"Слишком много неудачных попыток. Попробуйте через {config.LOGIN_WINDOW_MIN} минут."
        else:
            user = members.by_login(login_value)
            if user and hasher.verify(form.get("password", ""), user["password_hash"]):
                throttle.reset(login_value)
                request.session.clear()                       # новая сессия после входа
                request.session["uid"] = user["id"]
                nxt = request.query_params.get("next", "")
                default = "/coordinator" if user["role"] == "coordinator" else "/cabinet"
                return go(nxt if nxt.startswith("/") and not nxt.startswith("//") else default)
            throttle.fail(login_value, ip)
            error = "Неверный логин или пароль"
    return render(request, "login.html", error=error, login_value=login_value, status_code=401 if error else 200)


async def logout(request):
    if request.method == "POST":
        await checked_form(request)
        request.session.clear()
    return go("/")


# ================= волонтёр =================
@login_required("volunteer")
async def cabinet(request):
    return render(request, "cabinet.html", items=signups.of_member(request.state.user["id"]))


@login_required("volunteer")
async def signup_new(request):
    data, errors = {"action_id": request.query_params.get("action", "")}, {}
    if request.method == "POST":
        data = dict(await checked_form(request))
        form, errors = validate(SignupForm, data)
        if form:
            action = actions.get(form.action_id)
            if not action or action["action_date"] < date.today().isoformat():
                errors["action_id"] = "Выберите акцию из списка предстоящих"
            elif signups.exists(request.state.user["id"], form.action_id):
                errors["action_id"] = "Вы уже записаны на эту акцию"
        if not errors:
            signups.create(request.state.user["id"], form)
            flash(request, "ok", "Заявка отправлена координатору")
            return go("/cabinet")
    return render(request, "signup_new.html", actions=actions.upcoming(), tasks=TASKS, data=data, errors=errors,
                  status_code=400 if errors else 200)


# ================= координатор =================
@login_required("coordinator")
async def coordinator(request):
    return render(request, "coordinator.html", items=signups.all(), statuses=signups.statuses())


@login_required("coordinator")
async def change_status(request):
    form = await checked_form(request)
    status_ids = {s["id"] for s in signups.statuses()}
    try:
        signup_id, status_id = int(form.get("signup_id", 0)), int(form.get("status_id", 0))
    except ValueError:
        raise HTTPException(400, "Некорректные данные")
    if status_id not in status_ids:
        raise HTTPException(400, "Такого статуса нет")
    signups.set_status(signup_id, status_id)
    flash(request, "ok", f"Статус заявки № {signup_id} обновлён")
    return go("/coordinator")


# ================= ошибки и middleware =================
async def http_error(request, exc):
    return render(request, "error.html", code=exc.status_code, message=exc.detail, status_code=exc.status_code)


class CurrentUserMiddleware:
    """Кладёт текущего пользователя в request.state.user и добавляет защитные заголовки."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        uid = scope.get("session", {}).get("uid")
        scope.setdefault("state", {})["user"] = members.get(uid) if uid else None

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                h = message.setdefault("headers", [])
                h += [(b"x-content-type-options", b"nosniff"), (b"x-frame-options", b"DENY"),
                      (b"referrer-policy", b"same-origin"),
                      (b"content-security-policy", b"default-src 'self'; img-src 'self' data:; frame-ancestors 'none'")]
            await send(message)
        await self.app(scope, receive, send_with_headers)


routes = [
    Route("/", home),
    Route("/register", register, methods=["GET", "POST"]),
    Route("/login", login, methods=["GET", "POST"]),
    Route("/logout", logout, methods=["GET", "POST"]),
    Route("/cabinet", cabinet),
    Route("/signup", signup_new, methods=["GET", "POST"]),
    Route("/coordinator", coordinator),
    Route("/coordinator/status", change_status, methods=["POST"]),
    Mount("/static", StaticFiles(directory=config.BASE_DIR / "static"), name="static"),
]
middleware = [
    Middleware(SessionMiddleware, secret_key=config.SECRET_KEY, session_cookie="dg_session",
               max_age=config.SESSION_MAX_AGE, same_site="lax", https_only=config.HTTPS_ONLY),
    Middleware(CurrentUserMiddleware),
]
app = Starlette(routes=routes, middleware=middleware, exception_handlers={HTTPException: http_error})


def bootstrap() -> None:
    """Создаёт таблицы и координатора при первом запуске."""
    db.install()
    if not members.by_login("coordinator"):
        class Coordinator:
            login, full_name, email, phone = "coordinator", "Координатор Добрый Город", "coordinator@dobrygorod.ru", "+7 (495) 000-00-00"
        members.create(Coordinator, hasher.hash("Dobro2026!"), role="coordinator")


bootstrap()

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("PORT", 8000)))
