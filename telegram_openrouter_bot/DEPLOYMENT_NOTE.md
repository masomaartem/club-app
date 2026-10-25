# 📌 ЗАМІТКА ДЛЯ АГЕНТА: ПЕРЕНЕСЕННЯ ПРОЄКТУ НА СЕРВЕР

> **ВАЖЛИВО**: Цей проєкт повністю налаштований локально і очікує команди від користувача для розгортання на віддаленому сервері.

---

### 🖥 Дані сервера:
* **Хост:** `91.219.61.4` (резервний/минулий хост: `91.219.63.156`)
* **Користувач:** `artem.g15`
* **Команда SSH:** `ssh artem.g15@91.219.61.4`
* **Пароль:** `Artemik2013`
* **Цільова папка на сервері:** `/home/artem.g15/telegram_openrouter_bot`

---

### 📂 Локальне розташування файлів проєкту:
`C:\Users\User\telegram_openrouter_bot\`

---

### 🚀 Чекліст дій при команді «Підключися до сервера»:

1. **Підключення та перенесення файлів:**
   - Перенести всі файли проєкту з `C:\Users\User\telegram_openrouter_bot\` у `/home/artem.g15/telegram_openrouter_bot/`.
   - Обов'язково перенести готовий `.env` з налаштованими валідними токенами:
     - `TELEGRAM_BOT_TOKEN=<YOUR_TELEGRAM_BOT_TOKEN>` (@marma_ai_bot)
     - `OPENROUTER_API_KEY=<YOUR_OPENROUTER_API_KEY>`

2. **Права доступу та безпека:**
   - Виставити `chmod 600 /home/artem.g15/telegram_openrouter_bot/.env`.
   - Виставити `chmod +x /home/artem.g15/telegram_openrouter_bot/*.sh`.

3. **Розгортання та залежності:**
   - Запустити `./deploy_server.sh` або вручну:
     ```bash
     sudo apt-get update && sudo apt-get install -y python3 python3-venv sqlite3
     python3 -m venv venv
     ./venv/bin/pip install -r requirements.txt
     ```

4. **Автоматична перевірка (тести):**
   - Запустити `./venv/bin/python verify_all.py`.
   - Переконатися, що успішно пройдено перевірки:
     - Окремої пам'яті користувачів;
     - Кнопки «Новий чат»;
     - Стискання зі зменшеним порогом;
     - Стійкості до помилок API (історія не видаляється);
     - Оцінки токенів;
     - Збереження даних у SQLite після перезапуску;
     - Повернення робочого порогу до 50 повідомлень.

5. **Служба systemd (користувацька служба без потреби у sudo):**
   - Скопіювати `telegram-bot.service` у `~/.config/systemd/user/telegram-bot.service`.
   - Виконати:
     ```bash
     systemctl --user daemon-reload
     systemctl --user enable telegram-bot
     systemctl --user restart telegram-bot
     ```
   - Перевірити статус: `systemctl --user status telegram-bot --no-pager`.
   - Переглянути логи: `tail -f /home/artem.g15/telegram_openrouter_bot/bot.log`.

6. **Повідомити користувачеві:**
   - Назву служби: `telegram-bot`
   - Розташування файлів на сервері: `/home/artem.g15/telegram_openrouter_bot`
   - Команди керування (status, logs, stop, restart).
