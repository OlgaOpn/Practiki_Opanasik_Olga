#!/usr/bin/env bash
# Проверка «Доброго города» на MySQL (Ubuntu). Запуск из корня репозитория:
#     bash check_mysql.sh
# Нужны: MySQL 8 с базой dobry_gorod и пользователем dobry (см. README), python3 и python3-venv.
# Итог записывается в mysql_check_result.txt — его и скриншот терминала нужно приложить к отчёту.
set -u
DB_USER="${DB_USER:-dobry}"
DB_PASS="${DB_PASS:-Dobro2026!}"
DB_NAME="${DB_NAME:-dobry_gorod}"
PORT="${PORT:-8000}"
OUT="mysql_check_result.txt"
export DATABASE_URL="mysql://${DB_USER}:${DB_PASS}@localhost:3306/${DB_NAME}"
export SECRET_KEY="mysql-check"

exec > >(tee "$OUT") 2>&1
echo "=== Проверка «Доброго города» на MySQL — $(date '+%d.%m.%Y %H:%M') ==="
echo "Система: $(lsb_release -ds 2>/dev/null || uname -sr)"
echo "MySQL:   $(mysql --version)"
echo "Python:  $(python3 --version)"

echo; echo "--- 1. Виртуальное окружение и зависимости ---"
[ -d .venv ] || python3 -m venv .venv
. .venv/bin/activate
pip install -q -r requirements.txt && echo "зависимости установлены: $(pip freeze | grep -iE 'starlette|uvicorn|pymysql' | tr '\n' ' ')"

echo; echo "--- 2. Таблицы и демо-данные ---"
python seed_demo.py || echo "(демо-данные уже были в базе — оставлены как есть)"
MYSQL_PWD="$DB_PASS" mysql -u "$DB_USER" "$DB_NAME" -e "SHOW TABLES; SELECT COUNT(*) AS 'акций' FROM actions; SELECT COUNT(*) AS 'участников' FROM members; SELECT COUNT(*) AS 'заявок' FROM signups;"

echo; echo "--- 3. Запуск приложения ---"
python run.py --port "$PORT" > server.log 2>&1 &
SERVER=$!
trap 'kill $SERVER 2>/dev/null' EXIT
python - "$PORT" <<'PY'
import sys, time, urllib.request
for _ in range(50):
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{sys.argv[1]}/", timeout=1); break
    except OSError:
        time.sleep(0.2)
PY
echo "сервер: http://127.0.0.1:$PORT  (PID $SERVER)"

echo; echo "--- 4. Сценарии через HTTP ---"
python - "$PORT" <<'PY'
import http.cookiejar, re, sys, time, urllib.error, urllib.parse, urllib.request
BASE = f"http://127.0.0.1:{sys.argv[1]}"
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k): return None
class Client:
    def __init__(self):
        self.jar = http.cookiejar.CookieJar()
        self.op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar), NoRedirect)
    def req(self, path, data=None):
        body = urllib.parse.urlencode(data).encode() if data is not None else None
        try:
            r = self.op.open(BASE + path, body, timeout=10); return r.status, r.headers.get("Location", ""), r.read().decode()
        except urllib.error.HTTPError as e:
            return e.code, e.headers.get("Location", ""), e.read().decode()
    def form(self, path, data):
        _, _, page = self.req(path)
        tok = re.search(r'name="csrf_token" value="([^"]+)"', page).group(1)
        return self.req(path, dict(data, csrf_token=tok))
ok_all = True
def report(n, title, ok, detail):
    global ok_all; ok_all &= ok
    print(f"{n:>2}. [{'OK' if ok else 'ОШИБКА'}] {title} — {detail}")
stamp = time.strftime("%H%M%S")
g = Client(); st, _, html = g.req("/")
cards = len(re.findall(r'<article class="card[ "]', html))
report(1, "Главная страница", st == 200 and "Добрый город" in html, f"HTTP {st}, карточек акций: {cards}")
v = Client(); login = f"mysql.{stamp}"
st, loc, _ = v.form("/register", {"full_name": "Проверкина Ольга", "login": login, "email": f"{login}@mail.ru",
                                    "phone": "+7 (999) 123-45-67", "password": "Proverka1", "password2": "Proverka1"})
report(2, "Регистрация", st == 303 and loc.endswith("/login"), f"HTTP {st} → {loc}, логин {login}")
st, _, html = v.form("/register", {"full_name": "Проверкина Ольга", "login": login.upper(), "email": "x" + login + "@mail.ru",
                                    "phone": "+7 (999) 123-45-67", "password": "Proverka1", "password2": "Proverka1"})
report(3, "Тот же логин в другом регистре отклонён", st == 400 and "уже занят" in html, f"HTTP {st}")
st, loc, _ = v.form("/login", {"login": login, "password": "Proverka1"})
report(4, "Вход", st == 303 and loc == "/cabinet", f"HTTP {st} → {loc}")
_, _, page = v.req("/signup")
aid = re.search(r'<option value="(\d+)"', page).group(1)
st, loc, _ = v.form("/signup", {"action_id": aid, "task": "Фото и соцсети", "comment": "проверка на MySQL"})
report(5, "Заявка на акцию", st == 303 and loc == "/cabinet", f"HTTP {st}, акция № {aid}")
_, _, cab = v.req("/cabinet")
report(6, "Заявка в кабинете со статусом «Новая»", "Новая" in cab, "статус найден" if "Новая" in cab else "нет")
st, _, html = v.form("/login", {"login": "x' OR '1'='1' -- ", "password": "x' OR '1'='1"})
report(7, "SQL-инъекция во входе не срабатывает", st == 401, f"HTTP {st}")
c = Client(); st, loc, _ = c.form("/login", {"login": "coordinator", "password": "Dobro2026!"})
report(8, "Вход координатора", st == 303 and loc == "/coordinator", f"HTTP {st} → {loc}")
_, _, coord = c.req("/coordinator?status=1")
sid = re.findall(r'name="signup_id" value="(\d+)"', coord)
sid = max(map(int, sid)) if sid else None
_, _, page = c.req("/coordinator")
tok = re.search(r'name="csrf_token" value="([^"]+)"', page).group(1)
st, loc, _ = c.req("/coordinator/status", {"csrf_token": tok, "signup_id": str(sid), "status_id": "2"})
_, _, cab = v.req("/cabinet")
report(9, "Смена статуса Новая → Назначено", st == 303 and "Назначено" in cab, f"заявка № {sid}, HTTP {st}")
l = Client(); l.form("/login", {"login": "lisa.k", "password": "Volonter2026"})
_, _, cab = l.req("/cabinet")
m = re.search(r'href="/signups/(\d+)/review"', cab)
if m:
    st, loc, _ = l.form(f"/signups/{m.group(1)}/review", {"rating": "5", "body": "Проверка отзыва на MySQL: всё работает, спасибо!"})
    report(10, "Отзыв после завершённой акции", st == 303, f"заявка № {m.group(1)}, HTTP {st}")
else:
    report(10, "Отзыв после завершённой акции", "Ваш отзыв" in cab or "★" in cab, "отзыв уже был оставлен ранее")
c2 = Client(); c2.form("/login", {"login": "coordinator", "password": "Dobro2026!"})
_, _, page = c2.req("/coordinator/actions/new")
st, loc, _ = c2.form("/coordinator/actions/new", {"title": "Проверочная акция MySQL", "category": "Город", "action_date": "2027-03-14",
                                                  "place": "Москва, Тверская ул., 13", "description": "Акция создана скриптом проверки MySQL.", "needed": "3"})
_, _, adm = c2.req("/coordinator/actions")
report(11, "Создание акции координатором", st == 303 and "Проверочная акция MySQL" in adm, f"HTTP {st}")
print("\nИТОГ:", "все проверки пройдены" if ok_all else "есть ошибки — см. выше и server.log")
PY

echo; echo "--- 5. Данные в MySQL после проверки ---"
MYSQL_PWD="$DB_PASS" mysql -u "$DB_USER" "$DB_NAME" -e "
SELECT s.id, m.login, a.title, st.name AS status FROM signups s
  JOIN members m ON m.id = s.member_id JOIN actions a ON a.id = s.action_id JOIN signup_statuses st ON st.id = s.status_id
  ORDER BY s.id DESC LIMIT 5;
SELECT login, LEFT(password_hash, 22) AS hash_start, role FROM members ORDER BY id DESC LIMIT 3;
SELECT t.id, t.rating, LEFT(t.body, 40) AS body FROM testimonials t ORDER BY t.id DESC LIMIT 2;
SHOW INDEX FROM actions WHERE Key_name = 'ix_actions_date';"
echo; echo "Результат сохранён в $OUT"
