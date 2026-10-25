"""Секрети й налаштування з ~/app/.env у змінні оточення (заняття 02).

Служба systemd сама .env не читає, тому це робить програма — один раз, коли
будь-який модуль пише `import env`. Значення, які вже задано в оточенні,
не перезаписуються: так тести й перевірка можуть підставити свої.
"""
import os
from pathlib import Path

ENV_FILE = Path(__file__).parent / ".env"


def load_env(path=ENV_FILE):
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_env()
