#!/usr/bin/env bash
# Викочування нової версії. Заняття 09.
# Запускати з ~/app:  ./deploy.sh
set -euo pipefail

cd "$(dirname "$0")"

echo "==> 1/4 забираємо коміти з ~/repo.git"
git pull origin master

echo "==> 2/4 залежності"
.venv/bin/pip install -q -r requirements.txt 2>/dev/null || \
    .venv/bin/pip install -q fastapi uvicorn pyyaml

echo "==> 3/4 тести"
if [ -d tests ]; then
    $VENV/bin/python -m pytest -q tests || {
        echo "ТЕСТИ ЧЕРВОНІ — версію не викочуємо"; exit 1;
    }
fi

echo "==> 4/4 перезапуск служби"
systemctl --user restart club-api.service
sleep 2

if curl -fsS "http://127.0.0.1:$(grep -oP '(?<=--port )\d+' ~/.config/systemd/user/club-api.service)/api/ping" >/dev/null; then
    echo "ГОТОВО: сервіс відповідає"
else
    echo "СЕРВІС НЕ ВІДПОВІДАЄ. Дивись:  journalctl --user -u club-api -n 30"
    exit 1
fi
