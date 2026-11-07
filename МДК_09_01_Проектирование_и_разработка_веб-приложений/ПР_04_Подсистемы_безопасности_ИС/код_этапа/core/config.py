import os
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{BASE_DIR / 'dobry_gorod.db'}")
SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
HTTPS_ONLY = os.environ.get("HTTPS_ONLY", "0") == "1"
SESSION_MAX_AGE = 2 * 60 * 60
LOGIN_LIMIT = 5
LOGIN_WINDOW_MIN = 10
