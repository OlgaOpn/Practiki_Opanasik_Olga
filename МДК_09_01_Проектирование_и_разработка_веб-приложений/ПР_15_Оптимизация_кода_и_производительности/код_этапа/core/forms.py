import re
from datetime import date

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
            if e["type"] in ("int_parsing", "missing", "date_from_datetime_parsing", "date_parsing"):
                msg = {"action_id": "Выберите акцию", "rating": "Поставьте оценку от 1 до 5",
                       "needed": "Укажите число", "action_date": "Укажите дату"}.get(field, "Заполните поле")
            errors.setdefault(field, msg)
        return None, errors


CATEGORIES = ["Экология", "Животные", "Дети", "Пожилые люди", "Город"]


class ActionForm(BaseModel):
    title: str
    category: str
    action_date: date
    place: str
    description: str
    needed: int

    @field_validator("title")
    @classmethod
    def v_title(cls, v):
        v = clean(v)
        if not 5 <= len(v) <= 160:
            raise ValueError("Название — от 5 до 160 символов")
        return v

    @field_validator("category")
    @classmethod
    def v_category(cls, v):
        if v not in CATEGORIES:
            raise ValueError("Выберите направление")
        return v

    @field_validator("place")
    @classmethod
    def v_place(cls, v):
        v = clean(v)
        if not 5 <= len(v) <= 200:
            raise ValueError("Укажите адрес (от 5 символов)")
        return v

    @field_validator("description")
    @classmethod
    def v_description(cls, v):
        v = (v or "").strip()
        if not 20 <= len(v) <= 2000:
            raise ValueError("Описание — от 20 до 2000 символов")
        return v

    @field_validator("needed")
    @classmethod
    def v_needed(cls, v):
        if not 1 <= v <= 500:
            raise ValueError("Сколько нужно волонтёров: от 1 до 500")
        return v


class ReviewForm(BaseModel):
    rating: int
    body: str

    @field_validator("rating")
    @classmethod
    def v_rating(cls, v):
        if not 1 <= v <= 5:
            raise ValueError("Поставьте оценку от 1 до 5")
        return v

    @field_validator("body")
    @classmethod
    def v_body(cls, v):
        v = (v or "").strip()
        if not 10 <= len(v) <= 1000:
            raise ValueError("Отзыв — от 10 до 1000 символов")
        return v
