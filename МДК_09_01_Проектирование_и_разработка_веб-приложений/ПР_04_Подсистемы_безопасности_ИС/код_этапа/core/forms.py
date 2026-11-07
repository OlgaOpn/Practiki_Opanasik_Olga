import re

from pydantic import BaseModel, ValidationError, field_validator, model_validator

LOGIN_RE = re.compile(r"^[A-Za-z0-9._-]{3,24}$")
NAME_RE = re.compile(r"^[А-ЯЁа-яё]+(?:[ -][А-ЯЁа-яё]+)+$")
PHONE_RE = re.compile(r"^\+7 \(\d{3}\) \d{3}-\d{2}-\d{2}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-zА-Яа-я]{2,}$")
TASKS = ["Работа на площадке", "Встреча и регистрация участников", "Фото и соцсети", "Логистика и доставка"]


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


class RegistrationForm(BaseModel):
    login: str
    full_name: str
    email: str
    phone: str
    password: str
    password2: str

    @field_validator("login")
    @classmethod
    def v_login(cls, v):
        v = v.strip()
        if not LOGIN_RE.match(v):
            raise ValueError("Логин: 3–24 символа — латинские буквы, цифры, точка, дефис, подчёркивание")
        return v

    @field_validator("full_name")
    @classmethod
    def v_name(cls, v):
        v = clean(v)
        if len(v) > 120 or not NAME_RE.match(v):
            raise ValueError("Укажите фамилию и имя русскими буквами")
        return v

    @field_validator("email")
    @classmethod
    def v_email(cls, v):
        v = v.strip().lower()
        if len(v) > 120 or not EMAIL_RE.match(v):
            raise ValueError("Почта в формате name@example.ru")
        return v

    @field_validator("phone")
    @classmethod
    def v_phone(cls, v):
        v = v.strip()
        if not PHONE_RE.match(v):
            raise ValueError("Телефон в формате +7 (999) 123-45-67")
        return v

    @field_validator("password")
    @classmethod
    def v_password(cls, v):
        if len(v) < 8:
            raise ValueError("Пароль — не короче 8 символов")
        if not re.search(r"[A-Za-zА-Яа-яЁё]", v) or not re.search(r"\d", v):
            raise ValueError("В пароле нужны и буквы, и цифры")
        if v != v.strip():
            raise ValueError("Пароль не должен начинаться или заканчиваться пробелом")
        return v

    @model_validator(mode="after")
    def v_match(self):
        if self.password != self.password2:
            raise ValueError("password2|Пароли не совпадают")
        return self


class SignupForm(BaseModel):
    action_id: int
    task: str
    comment: str = ""

    @field_validator("task")
    @classmethod
    def v_task(cls, v):
        if v not in TASKS:
            raise ValueError("Выберите, чем хотите помочь")
        return v

    @field_validator("comment")
    @classmethod
    def v_comment(cls, v):
        v = (v or "").strip()
        if len(v) > 400:
            raise ValueError("Комментарий — не длиннее 400 символов")
        return v


def validate(model, data: dict):
    try:
        return model(**data), {}
    except ValidationError as exc:
        errors = {}
        for e in exc.errors():
            msg = str(e["msg"]).removeprefix("Value error, ")
            field = e["loc"][0] if e["loc"] else ""
            if "|" in msg:
                field, msg = msg.split("|", 1)
            if e["type"] in ("int_parsing", "missing"):
                msg = "Выберите акцию" if field == "action_id" else "Заполните поле"
            errors.setdefault(field, msg)
        return None, errors
