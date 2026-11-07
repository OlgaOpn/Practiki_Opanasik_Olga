"""Слой работы с базой данных: SQLite или MySQL.

Все запросы пишутся с плейсхолдером «?» и всегда параметризуются —
значения никогда не подставляются в текст SQL (защита от SQL-инъекций).
"""
import sqlite3
from datetime import date, datetime
from decimal import Decimal
from urllib.parse import unquote, urlparse

from .config import BASE_DIR


class Database:
    def __init__(self, url: str):
        self.url = url
        self.dialect = "mysql" if url.startswith("mysql") else "sqlite"
        self.queries = 0                      # счётчик запросов (для отладки)

    # ---------- соединение ----------
    def connect(self):
        if self.dialect == "sqlite":
            conn = sqlite3.connect(self.url.removeprefix("sqlite:///"))
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            return conn
        import pymysql                        # нужен только при работе с MySQL
        u = urlparse(self.url)
        return pymysql.connect(host=u.hostname, port=u.port or 3306, user=unquote(u.username or ""),
                               password=unquote(u.password or ""), database=u.path.lstrip("/"),
                               charset="utf8mb4", cursorclass=pymysql.cursors.DictCursor, autocommit=False)

    def _sql(self, sql: str) -> str:
        return sql.replace("?", "%s") if self.dialect == "mysql" else sql

    # ---------- запросы ----------
    def all(self, sql: str, params: tuple = ()) -> list[dict]:
        conn = self.connect()
        try:
            cur = conn.cursor()
            cur.execute(self._sql(sql), params)
            self.queries += 1
            return [self._row(r) for r in cur.fetchall()]
        finally:
            conn.close()

    @staticmethod
    def _row(r) -> dict:
        """Одинаковые типы для обеих СУБД: MySQL отдаёт даты объектами, SQLite — строками ISO."""
        row = dict(r)
        for k, v in row.items():
            if isinstance(v, datetime):
                row[k] = v.strftime("%Y-%m-%d %H:%M:%S")
            elif isinstance(v, date):
                row[k] = v.isoformat()
            elif isinstance(v, Decimal):
                row[k] = int(v) if v == v.to_integral_value() else float(v)
        return row

    def one(self, sql: str, params: tuple = ()) -> dict | None:
        rows = self.all(sql, params)
        return rows[0] if rows else None

    def run(self, sql: str, params: tuple = ()) -> int:
        """INSERT / UPDATE / DELETE. Возвращает id новой строки."""
        conn = self.connect()
        try:
            cur = conn.cursor()
            cur.execute(self._sql(sql), params)
            conn.commit()
            self.queries += 1
            return cur.lastrowid
        finally:
            conn.close()

    # ---------- создание таблиц ----------
    def install(self) -> None:
        script = (BASE_DIR / f"schema_{self.dialect}.sql").read_text(encoding="utf-8")
        conn = self.connect()
        try:
            if self.dialect == "sqlite":
                conn.executescript(script)
            else:
                cur = conn.cursor()
                for stmt in [s.strip() for s in script.split(";") if s.strip()]:
                    stmt = "\n".join(l for l in stmt.splitlines() if not l.strip().startswith("--")).strip()
                    if not stmt:
                        continue
                    try:
                        cur.execute(stmt)
                    except Exception as exc:          # повторный запуск: индекс уже существует
                        if "Duplicate key name" not in str(exc):
                            raise
            conn.commit()
        finally:
            conn.close()
