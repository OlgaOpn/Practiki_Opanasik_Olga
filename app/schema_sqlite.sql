-- «Добрый город» — схема БД для SQLite
CREATE TABLE IF NOT EXISTS members (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    login         VARCHAR(24)  NOT NULL UNIQUE COLLATE NOCASE,
    password_hash VARCHAR(255) NOT NULL,
    full_name     VARCHAR(120) NOT NULL,
    email         VARCHAR(120) NOT NULL UNIQUE COLLATE NOCASE,
    phone         VARCHAR(20)  NOT NULL,
    role          VARCHAR(12)  NOT NULL DEFAULT 'volunteer' CHECK (role IN ('volunteer', 'coordinator')),
    session_ver   INTEGER      NOT NULL DEFAULT 0,   -- растёт при выходе: старые cookie перестают действовать
    created_at    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS actions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       VARCHAR(160) NOT NULL,
    category    VARCHAR(30)  NOT NULL,
    action_date DATE         NOT NULL,
    place       VARCHAR(200) NOT NULL,
    description TEXT         NOT NULL,
    needed      INTEGER      NOT NULL DEFAULT 10 CHECK (needed > 0)
);

CREATE TABLE IF NOT EXISTS signup_statuses (
    id   INTEGER PRIMARY KEY,
    name VARCHAR(20) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS signups (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    member_id  INTEGER NOT NULL REFERENCES members(id) ON DELETE CASCADE,
    action_id  INTEGER NOT NULL REFERENCES actions(id) ON DELETE CASCADE,
    status_id  INTEGER NOT NULL DEFAULT 1 REFERENCES signup_statuses(id),
    task       VARCHAR(60)  NOT NULL,
    comment    VARCHAR(400),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (member_id, action_id)
);

CREATE TABLE IF NOT EXISTS testimonials (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    signup_id  INTEGER NOT NULL UNIQUE REFERENCES signups(id) ON DELETE CASCADE,
    body       TEXT    NOT NULL,
    rating     INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- журнал неудачных входов (ограничение подбора пароля)
CREATE TABLE IF NOT EXISTS login_failures (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    login      VARCHAR(24) NOT NULL COLLATE NOCASE,
    ip         VARCHAR(45) NOT NULL,
    created_at TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_failures_login ON login_failures (login, created_at);

-- ПР 15: индексы под частые запросы (фильтр по статусу, подсчёт заявок по акции, афиша по дате)
CREATE INDEX IF NOT EXISTS ix_signups_action ON signups (action_id);
CREATE INDEX IF NOT EXISTS ix_signups_status ON signups (status_id);
CREATE INDEX IF NOT EXISTS ix_actions_date ON actions (action_date);

INSERT OR IGNORE INTO signup_statuses (id, name) VALUES (1, 'Новая'), (2, 'Назначено'), (3, 'Завершено');
