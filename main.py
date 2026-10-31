"""Заготовка сервісу MARMAdrive. Учень дописує позначені місця, решту не чіпає.

Заняття 02 — тут вже є /api/ping і /api/about, додано /api/user та /api/plan.
Заняття 04 — додається GET списку.
Заняття 05 — додаються POST і DELETE.
"""
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

import yaml
from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, constr

import bot
from db import changed, execute, query  # готова заготовка, не редагуємо

BASE = Path(__file__).parent
CFG = yaml.safe_load((BASE / "project.yaml").read_text(encoding="utf-8"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    stop = bot.start_polling()              # бот живе стільки ж, скільки служба
    yield
    if stop:
        stop.set()


app = FastAPI(title=CFG["product"]["name"], lifespan=lifespan)

NameValue = constr(strip_whitespace=True, min_length=1, max_length=100)
NoteValue = constr(max_length=500)


class UserInput(BaseModel):
    name: NameValue
    note: NoteValue = ""
    username: str = ""


class UserNoteInput(BaseModel):
    note: NoteValue




@app.get("/api/ping")
def ping():
    """Перевірка, що служба жива. Використовує чекер заняття 02."""
    return {"status": "ok", "author": CFG["product"]["author"]}


@app.get("/api/about")
def about():
    """Дані з брифу. Чекер звіряє їх із project.yaml."""
    return {
        "name": CFG["product"]["name"],
        "author": CFG["product"]["author"],
        "features": CFG["product"].get("features", []),
    }


@app.get("/api/user")
def user():
    """Для кого цей сервіс. Дані беремо з project.yaml."""
    return {
        "product": CFG["product"]["name"],
        "for_whom": CFG["product"]["target_user"],
    }


@app.get("/api/plan")
def plan():
    """План розвитку сервісу (домашнє завдання заняття 02)."""
    return {
        "target_user": CFG["product"]["target_user"],
        "problem": (
            "Сергій зберігає посилання на рідкісні сорти пива, сайти "
            "броварень і специфікації в хаотичних нотатках і губить їх. "
            "Потрібен приватний каталог із можливістю генерувати публічні "
            "short-links для колег."
        ),
        "next": [
            "додати збереження закладок та посилань у базу даних SQLite (заняття 04)",
            "створити форму додавання нових лінків та управління приватністю (заняття 05)",
            "реалізувати дашборд зі швидким пошуком та Google Drive style short-links (заняття 06)",
        ],
    }


@app.exception_handler(404)
def not_found(request, exc):
    """Однаковий формат помилки для всього API — вимога контракту."""
    return JSONResponse({"error": "not_found"}, status_code=404)


# Заняття 04–05: список контактів і керування ними з адмінки.
@app.get("/api/users")
def list_users():
    return query(
        """SELECT id, chat_id, name, username, note, first_seen, last_seen, messages
           FROM users ORDER BY id"""
    )


@app.post("/api/users", status_code=201)
def create_user(data: UserInput):
    now = datetime.now().isoformat(timespec="seconds")
    user_id = execute(
        """INSERT INTO users(chat_id, name, username, note, first_seen, last_seen, messages)
           VALUES(NULL, ?, ?, ?, ?, ?, 0)""",
        (data.name, data.username.strip(), data.note, now, now),
    )
    return query(
        """SELECT id, chat_id, name, username, note, first_seen, last_seen, messages
           FROM users WHERE id = ?""",
        (user_id,),
    )[0]


@app.patch("/api/users/{user_id}")
def update_user(user_id: int, data: UserNoteInput):
    if changed("UPDATE users SET note = ? WHERE id = ?", (data.note, user_id)) == 0:
        raise HTTPException(status_code=404, detail="Контакт не знайдено")
    return query(
        """SELECT id, chat_id, name, username, note, first_seen, last_seen, messages
           FROM users WHERE id = ?""",
        (user_id,),
    )[0]


@app.delete("/api/users/{user_id}", status_code=204)
def delete_user(user_id: int):
    if changed("DELETE FROM users WHERE id = ?", (user_id,)) == 0:
        raise HTTPException(status_code=404, detail="Контакт не знайдено")
    return Response(status_code=204)
