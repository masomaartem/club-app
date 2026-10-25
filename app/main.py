"""Заготовка сервісу MARMAdrive. Учень дописує позначені місця, решту не чіпає.

Заняття 02 — тут вже є /api/ping і /api/about, додано /api/user та /api/plan.
Заняття 04 — додається GET списку.
Заняття 05 — додаються POST і DELETE.
"""
from contextlib import asynccontextmanager
from pathlib import Path

import yaml
from fastapi import FastAPI
from fastapi.responses import JSONResponse

import bot
from db import query  # готова заготовка, не редагуємо

BASE = Path(__file__).parent
CFG = yaml.safe_load((BASE / "project.yaml").read_text(encoding="utf-8"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    stop = bot.start_polling()              # бот живе стільки ж, скільки служба
    yield
    if stop:
        stop.set()


app = FastAPI(title=CFG["product"]["name"], lifespan=lifespan)


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
