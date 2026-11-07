from datetime import date

from .db import Database


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


class ActionRepository:
    def __init__(self, db: Database):
        self.db = db

    def upcoming(self):
        return self.db.all("SELECT * FROM actions WHERE action_date >= ? ORDER BY action_date", (date.today().isoformat(),))

    def all(self):
        return self.db.all("SELECT * FROM actions ORDER BY action_date DESC")

    def get(self, action_id: int):
        return self.db.one("SELECT * FROM actions WHERE id = ?", (action_id,))


class SignupRepository:
    SELECT = """
        SELECT s.id, s.member_id, s.action_id, s.status_id, s.task, s.comment, s.created_at,
               st.name AS status, a.title, a.action_date, a.place, a.category,
               m.full_name, m.login, m.phone, m.email
        FROM signups s
        JOIN signup_statuses st ON st.id = s.status_id
        JOIN actions a ON a.id = s.action_id
        JOIN members m ON m.id = s.member_id"""

    def __init__(self, db: Database):
        self.db = db

    def create(self, member_id: int, form) -> int:
        return self.db.run("INSERT INTO signups (member_id, action_id, task, comment) VALUES (?, ?, ?, ?)",
                           (member_id, form.action_id, form.task, form.comment))

    def exists(self, member_id: int, action_id: int) -> bool:
        return self.db.one("SELECT id FROM signups WHERE member_id = ? AND action_id = ?", (member_id, action_id)) is not None

    def of_member(self, member_id: int):
        return self.db.all(self.SELECT + " WHERE s.member_id = ? ORDER BY a.action_date DESC", (member_id,))

    def all(self):
        return self.db.all(self.SELECT + " ORDER BY s.id DESC")

    def statuses(self):
        return self.db.all("SELECT * FROM signup_statuses ORDER BY id")

    def set_status(self, signup_id: int, status_id: int) -> None:
        self.db.run("UPDATE signups SET status_id = ? WHERE id = ?", (status_id, signup_id))
