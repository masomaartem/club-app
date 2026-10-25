"""Перевір бота без Telegram — так само його перевіряє автоперевірка.

    python3 try_bot.py "/start"
    python3 try_bot.py "/ask що таке API?"
    python3 try_bot.py --id 5 --name Оля "привіт"     від імені іншої людини
"""
import argparse
import os

os.environ.setdefault("BOT_POLLING", "0")    # справжній polling тут не потрібен

import bot  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("text", help="що написати боту")
ap.add_argument("--id", type=int, default=1, help="номер чату (у Telegram — chat_id)")
ap.add_argument("--name", default="Тест", help="ім'я того, хто пише")
a = ap.parse_args()

update = {"update_id": 0, "message": {
    "message_id": 1,
    "chat": {"id": a.id, "type": "private"},
    "from": {"id": a.id, "is_bot": False, "first_name": a.name},
    "text": a.text,
}}
reply = bot.handle_update(update)
print(reply if reply is not None else "(бот нічого не відповів — на порожній текст так і має бути)")
