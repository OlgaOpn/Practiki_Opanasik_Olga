"""Демо-данные для свежей базы: 6 акций, 3 волонтёра, 6 заявок, 1 отзыв.
Запуск из корня репозитория:  python seed_demo.py   (база берётся из DATABASE_URL, по умолчанию SQLite app/dobry_gorod.db)
Пароль у всех волонтёров: Volonter2026"""
from datetime import date, timedelta

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "app"))
from main import db, hasher, members  # noqa: E402  (создаёт таблицы и координатора, если их нет)

if db.one("SELECT COUNT(*) AS n FROM actions")["n"]:
    raise SystemExit("В базе уже есть данные — демо-данные не добавлены.")

today = date.today()
D = lambda days: (today + timedelta(days=days)).isoformat()
ACTIONS = [
    ("Субботник в Измайловском парке", "Экология", D(-21), "Москва, Измайловский парк, вход с Аллеи Большого Круга",
     "Убираем листву и мусор вдоль прудов, красим скамейки. Перчатки, мешки и горячий чай — от организаторов.", 25),
    ("Сбор корма для приюта «Верный друг»", "Животные", D(-7), "Москва, ул. Бутлерова, 12, пункт сбора",
     "Принимаем и сортируем корм и медикаменты, грузим машину для приюта.", 8),
    ("Посадка деревьев на ВДНХ", "Экология", D(14), "Москва, ВДНХ, Ботанический сад, южный вход",
     "Сажаем 120 саженцев липы и клёна вместе с дендрологами. Подойдёт без опыта.", 40),
    ("Мастерская для детей из центра «Солнце»", "Дети", D(21), "Москва, Каширское шоссе, 54, центр «Солнце»",
     "Проводим творческую мастерскую: рисуем, лепим и собираем ёлочные игрушки.", 6),
    ("Новогодние открытки для дома престарелых", "Пожилые люди", D(35), "Москва, библиотека им. Некрасова",
     "Пишем и рисуем открытки, а потом вместе поздравляем бабушек и дедушек.", 15),
    ("Помощь на благотворительном забеге «5 км добра»", "Город", D(63), "Москва, Парк Горького, Пушкинская набережная",
     "Встречаем бегунов, выдаём воду и стартовые пакеты, работаем на финише.", 30),
]
for a in ACTIONS:
    db.run("INSERT INTO actions (title, category, action_date, place, description, needed) VALUES (?, ?, ?, ?, ?, ?)", a)


class Person:
    def __init__(self, login, full_name, email, phone):
        self.login, self.full_name, self.email, self.phone = login, full_name, email, phone


PEOPLE = [Person("sokolova.v", "Соколова Варвара", "v.sokolova@mail.ru", "+7 (916) 482-15-30"),
          Person("timur_n", "Набиев Тимур", "timur.nabiev@yandex.ru", "+7 (903) 227-64-81"),
          Person("lisa.k", "Карпова Елизавета", "lisa.karpova@gmail.com", "+7 (925) 610-09-44")]
ids = {p.login: members.create(p, hasher.hash("Volonter2026")) for p in PEOPLE}
SIGNUPS = [("sokolova.v", 1, "Работа на площадке", "", 3), ("sokolova.v", 3, "Фото и соцсети", "Возьму свой фотоаппарат", 1),
           ("timur_n", 2, "Логистика и доставка", "Есть машина", 3), ("timur_n", 6, "Встреча и регистрация участников", "", 2),
           ("lisa.k", 1, "Фото и соцсети", "", 3), ("lisa.k", 4, "Работа на площадке", "Работала вожатой", 1)]
for login, action_id, task, comment, status in SIGNUPS:
    db.run("INSERT INTO signups (member_id, action_id, task, comment, status_id) VALUES (?, ?, ?, ?, ?)",
           (ids[login], action_id, task, comment, status))
if db.one("SELECT COUNT(*) AS n FROM testimonials")["n"] == 0:
    db.run("INSERT INTO testimonials (signup_id, body, rating) VALUES (?, ?, ?)",
           (1, "Отличная команда! За три часа убрали весь берег у Серебряного пруда, а в конце был горячий чай.", 5))
print(f"Готово: акций {len(ACTIONS)}, волонтёров {len(PEOPLE)}, заявок {len(SIGNUPS)}")
