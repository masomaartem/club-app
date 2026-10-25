"""Заняття 06: бот питає безкоштовну ШІ через API, сумісний з OpenRouter.

Куди й з яким ключем ходити — лише в ~/app/.env:
    LLM_BASE_URL=http://127.0.0.1/llm/v1   шкільний шлюз (учням до 18 років)
    LLM_BASE_URL=https://openrouter.ai/api/v1   власний акаунт (з 18 років)
    LLM_API_KEY=...                         ключ (для шлюзу школи — будь-який текст)
    LLM_MODEL=...                           модель з позначкою :free
Код від цього не змінюється.
"""
import json
import os
import urllib.error
import urllib.request

import env  # noqa: F401  — читає ~/app/.env

BASE_URL = os.environ.get("LLM_BASE_URL", "http://127.0.0.1/llm/v1").rstrip("/")
API_KEY = os.environ.get("LLM_API_KEY", "")
MODEL = os.environ.get("LLM_MODEL", "openrouter/free")

SYSTEM = ("Ти — помічник у Telegram-боті школяра. Відповідай українською, коротко "
          "(до 5 речень) і зрозуміло для підлітка. Якщо тобі дали фрагменти бази "
          "знань — спирайся насамперед на них, а якщо там відповіді немає, так і скажи.")


def ask(question, context=None):
    """Питання → текст відповіді. Ніколи не кидає виняток: на будь-яку
    біду повертає зрозуміле людині повідомлення."""
    messages = [{"role": "system", "content": SYSTEM}]
    if context:
        messages.append({"role": "system",
                         "content": "Фрагменти бази знань:\n\n" + "\n---\n".join(context)})
    messages.append({"role": "user", "content": question})
    body = json.dumps({"model": MODEL, "messages": messages, "max_tokens": 400}).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}/chat/completions", data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"].strip()
    except urllib.error.HTTPError as e:
        if e.code == 429:
            return "ШІ зараз перевантажений або на сьогодні вичерпано ліміт запитів. Спробуй пізніше."
        if e.code in (401, 403):
            return "ШІ не пускає: перевір LLM_API_KEY у файлі .env."
        if e.code == 503:
            return "ШІ школи ще не підключено. Скажи викладачу."
        return f"ШІ відповів помилкою {e.code}. Спробуй пізніше."
    except (urllib.error.URLError, TimeoutError, OSError, KeyError, IndexError, ValueError):
        return "Не вдалося дістатися до ШІ. Спробуй пізніше."
