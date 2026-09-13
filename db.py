"""Робота з базою. Готова заготовка — учень її не редагує (заняття 04).

Учень пише лише SQL у своїх ендпоінтах, а підключення, закриття
з'єднання й перетворення рядків у JSON бере звідси.
"""
import sqlite3
from pathlib import Path

import yaml

BASE = Path(__file__).parent
CFG = yaml.safe_load((BASE / "project.yaml").read_text(encoding="utf-8"))
DB_PATH = Path.home() / "data" / CFG["database"]["file"]


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row          # щоб рядок став схожим на словник
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def query(sql, params=()):
    """SELECT: повертає список словників, готовий віддати як JSON."""
    with connect() as conn:
        return [dict(row) for row in conn.execute(sql, params)]


def execute(sql, params=()):
    """INSERT / UPDATE / DELETE: повертає id останнього доданого рядка.

    Параметри передаються окремо від тексту запиту — саме тому
    SQL-ін'єкція тут не спрацює (заняття 08).
    """
    with connect() as conn:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.lastrowid
