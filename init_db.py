"""Створює таблиці бази. Можна запускати скільки завгодно разів:
CREATE TABLE IF NOT EXISTS не чіпає те, що вже є.

    python3 init_db.py
"""
from db import DB_PATH, connect

SCHEMA = """
-- заняття 04: усі, хто писав боту, і контакти, додані з адмінки
CREATE TABLE IF NOT EXISTS users (
    id         INTEGER PRIMARY KEY,
    chat_id    INTEGER UNIQUE,              -- порожнє, якщо контакт додано вручну
    name       TEXT    NOT NULL,
    username   TEXT    NOT NULL DEFAULT '',
    note       TEXT    NOT NULL DEFAULT '',
    first_seen TEXT    NOT NULL,
    last_seen  TEXT    NOT NULL,
    messages   INTEGER NOT NULL DEFAULT 0
);

"""


def main():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with connect() as conn:
        conn.executescript(SCHEMA)
    print(f"таблиці готові: {DB_PATH}")


if __name__ == "__main__":
    main()
