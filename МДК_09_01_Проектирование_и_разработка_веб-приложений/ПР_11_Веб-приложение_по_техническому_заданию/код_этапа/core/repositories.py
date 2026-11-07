from datetime import date

from .db import Database


def today() -> str:
    return date.today().isoformat()


class MemberRepository:
    def __init__(self, db: Database):
        self.db = db

    def get(self, member_id: int):
        return self.db.one("SELECT id, login, full_name, email, phone, role FROM members WHERE id = ?", (member_id,))

    def by_login(self, login: str):
        return self.db.one("SELECT * FROM members WHERE LOWER(login) = LOWER(?)", (login,))

    def email_taken(self, email: str) -> bool:
        return self.db.one("SELECT id FROM members WHERE LOWER(email) = LOWER(?)", (email,)) is not None

    def create(self, form, password_hash: str, role: str = "volunteer") -> int:
        return self.db.run(
            "INSERT INTO members (login, password_hash, full_name, email, phone, role) VALUES (?, ?, ?, ?, ?, ?)",
            (form.login, password_hash, form.full_name, form.email, form.phone, role))

    def count_volunteers(self) -> int:
        return self.db.one("SELECT COUNT(*) AS n FROM members WHERE role = 'volunteer'")["n"]


class ActionRepository:
    def __init__(self, db: Database):
        self.db = db

    def upcoming(self, category: str | None = None):
        if category:
            return self.db.all("SELECT * FROM actions WHERE action_date >= ? AND category = ? ORDER BY action_date",
                               (today(), category))
        return self.db.all("SELECT * FROM actions WHERE action_date >= ? ORDER BY action_date", (today(),))

    def all(self):
        return self.db.all("SELECT * FROM actions ORDER BY action_date DESC")

    def get(self, action_id: int):
        return self.db.one("SELECT * FROM actions WHERE id = ?", (action_id,))

    def create(self, f) -> int:
        return self.db.run("INSERT INTO actions (title, category, action_date, place, description, needed) VALUES (?, ?, ?, ?, ?, ?)",
                           (f.title, f.category, f.action_date.isoformat(), f.place, f.description, f.needed))

    def update(self, action_id: int, f) -> None:
        self.db.run("UPDATE actions SET title = ?, category = ?, action_date = ?, place = ?, description = ?, needed = ? WHERE id = ?",
                    (f.title, f.category, f.action_date.isoformat(), f.place, f.description, f.needed, action_id))

    def delete(self, action_id: int) -> None:
        self.db.run("DELETE FROM actions WHERE id = ?", (action_id,))


class SignupRepository:
    SELECT = """
        SELECT s.id, s.member_id, s.action_id, s.status_id, s.task, s.comment, s.created_at,
               st.name AS status, a.title, a.action_date, a.place, a.category,
               m.full_name, m.login, m.phone, m.email
        FROM signups s
        JOIN signup_statuses st ON st.id = s.status_id
        JOIN actions a ON a.id = s.action_id
        JOIN members m ON m.id = s.member_id"""
    NEW, ASSIGNED, DONE = 1, 2, 3

    def __init__(self, db: Database):
        self.db = db

    def create(self, member_id: int, form) -> int:
        return self.db.run("INSERT INTO signups (member_id, action_id, task, comment) VALUES (?, ?, ?, ?)",
                           (member_id, form.action_id, form.task, form.comment))

    def get(self, signup_id: int):
        return self.db.one(self.SELECT + " WHERE s.id = ?", (signup_id,))

    def exists(self, member_id: int, action_id: int) -> bool:
        return self.db.one("SELECT id FROM signups WHERE member_id = ? AND action_id = ?", (member_id, action_id)) is not None

    def count_for_action(self, action_id: int) -> int:
        return self.db.one("SELECT COUNT(*) AS n FROM signups WHERE action_id = ?", (action_id,))["n"]

    def count_with_status(self, status_id: int) -> int:
        return self.db.one("SELECT COUNT(*) AS n FROM signups WHERE status_id = ?", (status_id,))["n"]

    def of_member(self, member_id: int):
        return self.db.all(self.SELECT + " WHERE s.member_id = ? ORDER BY a.action_date DESC", (member_id,))

    def all(self, status_id: int | None = None):
        if status_id:
            return self.db.all(self.SELECT + " WHERE s.status_id = ? ORDER BY s.id DESC", (status_id,))
        return self.db.all(self.SELECT + " ORDER BY s.id DESC")

    def statuses(self):
        return self.db.all("SELECT * FROM signup_statuses ORDER BY id")

    def set_status(self, signup_id: int, status_id: int) -> None:
        self.db.run("UPDATE signups SET status_id = ? WHERE id = ?", (status_id, signup_id))

    def delete(self, signup_id: int) -> None:
        self.db.run("DELETE FROM signups WHERE id = ?", (signup_id,))


class TestimonialRepository:
    def __init__(self, db: Database):
        self.db = db

    def for_signup(self, signup_id: int):
        return self.db.one("SELECT * FROM testimonials WHERE signup_id = ?", (signup_id,))

    def create(self, signup_id: int, form) -> int:
        return self.db.run("INSERT INTO testimonials (signup_id, body, rating) VALUES (?, ?, ?)", (signup_id, form.body, form.rating))

    def latest(self, limit: int = 3):
        rows = self.db.all("SELECT * FROM testimonials ORDER BY created_at DESC LIMIT ?", (limit,))
        for r in rows:
            info = self.db.one("""SELECT m.full_name, a.title FROM signups s JOIN members m ON m.id = s.member_id
                                  JOIN actions a ON a.id = s.action_id WHERE s.id = ?""", (r["signup_id"],))
            r.update(info or {})
        return rows
