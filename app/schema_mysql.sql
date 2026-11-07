-- «Добрый город» — схема БД для MySQL 8 (кодировка utf8mb4)
CREATE TABLE IF NOT EXISTS members (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    login         VARCHAR(24)  NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name     VARCHAR(120) NOT NULL,
    email         VARCHAR(120) NOT NULL UNIQUE,
    phone         VARCHAR(20)  NOT NULL,
    role          ENUM('volunteer', 'coordinator') NOT NULL DEFAULT 'volunteer',
    session_ver   INT NOT NULL DEFAULT 0,          -- растёт при выходе: старые cookie перестают действовать
    created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS actions (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    title       VARCHAR(160) NOT NULL,
    category    VARCHAR(30)  NOT NULL,
    action_date DATE         NOT NULL,
    place       VARCHAR(200) NOT NULL,
    description TEXT         NOT NULL,
    needed      INT          NOT NULL DEFAULT 10 CHECK (needed > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS signup_statuses (
    id   INT PRIMARY KEY,
    name VARCHAR(20) NOT NULL UNIQUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS signups (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    member_id  INT NOT NULL,
    action_id  INT NOT NULL,
    status_id  INT NOT NULL DEFAULT 1,
    task       VARCHAR(60) NOT NULL,
    comment    VARCHAR(400),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_member_action (member_id, action_id),
    FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE,
    FOREIGN KEY (action_id) REFERENCES actions(id) ON DELETE CASCADE,
    FOREIGN KEY (status_id) REFERENCES signup_statuses(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS testimonials (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    signup_id  INT NOT NULL UNIQUE,
    body       TEXT NOT NULL,
    rating     TINYINT NOT NULL CHECK (rating BETWEEN 1 AND 5),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (signup_id) REFERENCES signups(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS login_failures (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    login      VARCHAR(24) NOT NULL,
    ip         VARCHAR(45) NOT NULL,
    created_at TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX ix_failures_login (login, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ПР 15: индексы под частые запросы (в MySQL внешние ключи уже индексированы, добавляем дату акции)
CREATE INDEX ix_actions_date ON actions (action_date);

INSERT IGNORE INTO signup_statuses (id, name) VALUES (1, 'Новая'), (2, 'Назначено'), (3, 'Завершено');
