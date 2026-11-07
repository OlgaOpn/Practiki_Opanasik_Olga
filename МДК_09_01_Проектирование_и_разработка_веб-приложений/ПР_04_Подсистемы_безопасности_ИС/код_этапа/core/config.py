"""Настройки приложения. Значения берутся из переменных окружения."""
import os
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# sqlite:///путь/к/файлу.db  или  mysql://пользователь:пароль@хост:3306/база
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{BASE_DIR / 'dobry_gorod.db'}")
SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
# в рабочей среде (HTTPS) cookie сессии передаётся только по защищённому соединению
HTTPS_ONLY = os.environ.get("HTTPS_ONLY", "0") == "1"
SESSION_MAX_AGE = 2 * 60 * 60          # сессия живёт 2 часа
LOGIN_LIMIT = 5                        # неудачных попыток входа...
LOGIN_WINDOW_MIN = 10                  # ...за столько минут — и вход блокируется
