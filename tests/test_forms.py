"""Автотест форм регистрации и входа «Доброго города» (МДК.05.03, задание 3).

Запускает приложение на временной базе SQLite с демо-данными и отправляет формы
обычными HTTP-запросами (как браузер с выключенным JavaScript) — проверяется серверная валидация.
Выполняет 22 из 41 проверки таблицы «Результаты_проверок.xlsx»; проверки, которым нужен
браузер (маска телефона, подсказки на JavaScript, перенос данных в форме), выполнены вручную.
Скриншоты не делает. Результаты сохраняет в tests/results.csv.

    python -m unittest tests/test_forms.py -v        (из корня репозитория)
"""
import csv
import http.cookiejar
import os
import re
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PORT = int(os.environ.get("TEST_PORT", 8765))
BASE = f"http://127.0.0.1:{PORT}"
GOOD = {"full_name": "Проверкина Ольга", "login": "auto.user", "email": "auto.user@mail.ru",
        "phone": "+7 (999) 123-45-67", "password": "Proverka1", "password2": "Proverka1"}
RESULTS = []


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class Client:
    """Мини-браузер: хранит cookie, достаёт CSRF-токен из формы, не следует редиректам."""
    def __init__(self):
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar), NoRedirect)

    def request(self, path, data=None):
        body = urllib.parse.urlencode(data).encode() if data is not None else None
        try:
            r = self.opener.open(BASE + path, body, timeout=10)
            return r.status, r.headers, r.read().decode()
        except urllib.error.HTTPError as e:
            return e.code, e.headers, e.read().decode()

    def submit(self, path, data, with_csrf=True):
        _, _, page = self.request(path)
        token = re.search(r'name="csrf_token" value="([^"]+)"', page).group(1)
        return self.request(path, dict(data, csrf_token=token) if with_csrf else data)


def errors(html):
    return [re.sub(r"<[^>]+>", "", e).strip() for e in re.findall(r'class="field__err"[^>]*>(.*?)</', html, re.S) if e.strip()]


class FormsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        env = dict(os.environ, DATABASE_URL=f"sqlite:///{cls.tmp}/test.db", SECRET_KEY="test-secret")
        subprocess.run([sys.executable, "seed_demo.py"], cwd=ROOT, env=env, check=True, capture_output=True)
        cls.server = subprocess.Popen([sys.executable, "run.py", "--port", str(PORT)], cwd=ROOT, env=env,
                                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(100):
            try:
                urllib.request.urlopen(BASE + "/", timeout=1)
                break
            except OSError:
                time.sleep(0.1)

    @classmethod
    def tearDownClass(cls):
        cls.server.terminate()
        cls.server.wait()
        with open(ROOT / "tests" / "results.csv", "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(["ID", "Проверка", "Ожидается", "Получено", "Результат"])
            w.writerows(sorted(RESULTS))

    def check(self, cid, title, expected, actual, ok):
        RESULTS.append([cid, title, expected, actual, "пройден" if ok else "не пройден"])
        self.assertTrue(ok, f"{cid} {title}: {actual}")

    # ---------- регистрация ----------
    def register(self, cid, title, changes, expect_ok, expected, must_contain=None):
        status, headers, html = Client().submit("/register", dict(GOOD, **changes))
        created = status == 303 and headers.get("Location", "").endswith("/login")
        errs = errors(html)
        actual = "аккаунт создан (303 → /login)" if created else f"HTTP {status}; " + "; ".join(errs)
        ok = created == expect_ok and (must_contain is None or any(must_contain in e for e in errs))
        self.check(cid, title, expected, actual, ok)

    def test_r01_valid(self):
        self.register("Р01", "Все поля заполнены верно", {"login": "auto.r01", "email": "r01@mail.ru"}, True, "аккаунт создан")

    def test_r02_login_min(self):
        self.register("Р02", "Логин из 3 символов", {"login": "a_b", "email": "r02@mail.ru"}, True, "аккаунт создан")

    def test_r03_login_short(self):
        self.register("Р03", "Логин из 2 символов", {"login": "ab"}, False, "отказ", "3–24")

    def test_r04_login_max(self):
        self.register("Р04", "Логин из 24 символов", {"login": "b" * 23 + "2", "email": "r04@mail.ru"}, True, "аккаунт создан")

    def test_r05_login_long(self):
        self.register("Р05", "Логин из 25 символов", {"login": "c" * 25}, False, "отказ", "3–24")

    def test_r06_login_cyrillic(self):
        self.register("Р06", "Логин с кириллицей", {"login": "ольга"}, False, "отказ")

    def test_r08_login_taken(self):
        self.register("Р08", "Логин занят", {"login": "timur_n"}, False, "отказ «Этот логин уже занят»", "уже занят")

    def test_r09_login_taken_case(self):
        self.register("Р09", "Занятый логин в другом регистре", {"login": "TIMUR_N"}, False, "отказ «Этот логин уже занят»", "уже занят")

    def test_r10_email_taken(self):
        self.register("Р10", "Почта занята (другой регистр)", {"login": "auto.r10", "email": "V.SOKOLOVA@MAIL.RU"}, False,
                      "отказ «уже зарегистрирован»", "уже зарегистрирован")

    def test_r12_password_short(self):
        self.register("Р12", "Пароль 7 символов", {"login": "auto.r12", "password": "abcde12", "password2": "abcde12"}, False, "отказ", "8")

    def test_r13_password_digits(self):
        self.register("Р13", "Пароль только из цифр", {"login": "auto.r13", "password": "12345678", "password2": "12345678"}, False, "отказ")

    def test_r15_password_mismatch(self):
        self.register("Р15", "Пароли не совпадают", {"login": "auto.r15", "password2": "Proverka2"}, False, "отказ", "не совпадают")

    def test_r16_name_one_word(self):
        self.register("Р16", "ФИО одним словом", {"login": "auto.r16", "full_name": "Ольга"}, False, "отказ")

    def test_r20_phone_without_mask(self):
        self.register("Р20", "Телефон без маски", {"login": "auto.r20", "phone": "89991234567"}, False, "отказ", "+7 (999)")

    def test_r21_email_no_tld(self):
        self.register("Р21", "Почта без домена верхнего уровня", {"login": "auto.r21", "email": "olga@mail"}, False, "отказ")

    def test_r23_empty_form(self):
        status, _, html = Client().submit("/register", {k: "" for k in GOOD})
        n = len(errors(html))
        self.check("Р23", "Пустая форма (без JavaScript)", "HTTP 400, ошибки под 5 полями (повтор пароля сверяется с паролем)", f"HTTP {status}, ошибок: {n}", status == 400 and n == 5)

    def test_r26_no_csrf(self):
        status, _, _ = Client().submit("/register", dict(GOOD, login="auto.r26"), with_csrf=False)
        self.check("Р26", "POST без CSRF-токена", "HTTP 403", f"HTTP {status}", status == 403)

    # ---------- вход ----------
    def login(self, cid, title, login, password, expect_ok, expected):
        status, headers, html = Client().submit("/login", {"login": login, "password": password})
        ok_login = status == 303
        actual = f"303 → {headers.get('Location')}" if ok_login else f"HTTP {status}" + (" «Неверный логин или пароль»" if "Неверный логин" in html else "")
        self.check(cid, title, expected, actual, ok_login == expect_ok)

    def test_v01_volunteer(self):
        self.login("В01", "Вход волонтёра", "sokolova.v", "Volonter2026", True, "303 → /cabinet")

    def test_v03_login_case(self):
        self.login("В03", "Логин в другом регистре", "SOKOLOVA.V", "Volonter2026", True, "вход выполнен")

    def test_v04_wrong_password(self):
        self.login("В04", "Неверный пароль", "lisa.k", "Volonter2025", False, "HTTP 401")

    def test_v06_sql_injection(self):
        self.login("В06", "SQL-инъекция в логине", "' OR '1'='1' --", "' OR '1'='1", False, "вход не выполнен")

    def test_v13_cookie_after_logout(self):
        c = Client()
        c.submit("/login", {"login": "lisa.k", "password": "Volonter2026"})
        stolen = [(k.name, k.value) for k in c.jar if k.name == "dg_session"][0]
        _, _, page = c.request("/cabinet")
        token = re.search(r'name="csrf_token" value="([^"]+)"', page).group(1)
        c.request("/logout", {"csrf_token": token})
        req = urllib.request.Request(BASE + "/cabinet", headers={"Cookie": f"{stolen[0]}={stolen[1]}"})
        try:
            r = urllib.request.build_opener(NoRedirect).open(req, timeout=10)
            status, location = r.status, ""
        except urllib.error.HTTPError as e:
            status, location = e.code, e.headers.get("Location", "")
        self.check("В13", "Cookie, сохранённая до выхода, после выхода", "303 → /login",
                   f"HTTP {status}" + (f" → {location}" if location else " — кабинет открыт"), status == 303 and "/login" in location)


if __name__ == "__main__":
    unittest.main(verbosity=2)
