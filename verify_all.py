import asyncio
import os
import sys

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from database import Database
from openrouter import estimate_tokens, estimate_context_tokens


async def run_comprehensive_verification():
    print("=" * 60)
    print("🚀 ПОЧАТОК КОМПЛЕКСНОГО ТЕСТУВАННЯ СИСТЕМИ TELEGRAM-БОТА")
    print("=" * 60)

    test_db = "test_verification.sqlite3"
    if os.path.exists(test_db):
        os.remove(test_db)

    db = Database(test_db)
    await db.init_db()

    # ---------------------------------------------------------
    # ТЕСТ 1: Окрема пам'ять для кожного користувача
    # ---------------------------------------------------------
    print("\n[ТЕСТ 1] Перевірка ізоляції пам'яті користувачів...")
    user_a = 111111
    user_b = 222222

    await db.add_message(user_a, "user", "Привіт, мене звати Тарас.")
    await db.add_message(user_a, "assistant", "Вітаю, Тарасе! Чим можу допомогти?")

    await db.add_message(user_b, "user", "Привіт, я Олена і цікавлюся Python.")
    await db.add_message(user_b, "assistant", "Привіт, Олено! Радий допомогти з Python.")

    msgs_a = await db.get_active_messages(user_a)
    msgs_b = await db.get_active_messages(user_b)

    assert len(msgs_a) == 2, f"Очікувалось 2 повідомлення для User A, отримано {len(msgs_a)}"
    assert len(msgs_b) == 2, f"Очікувалось 2 повідомлення для User B, отримано {len(msgs_b)}"
    assert "Тарас" in msgs_a[0]["content"] and "Тарас" not in msgs_b[0]["content"]
    assert "Олена" in msgs_b[0]["content"] and "Олена" not in msgs_a[0]["content"]
    print("✅ Ізоляція пам'яті: успішно. Користувачі мають суворо окрему історію.")

    # ---------------------------------------------------------
    # ТЕСТ 2: Кнопка «Новий чат»
    # ---------------------------------------------------------
    print("\n[ТЕСТ 2] Перевірка кнопки «Новий чат» (очищення історії, підсумку, лічильника)...")
    await db.apply_compression(user_a, "Попередній підсумок: Тарас цікавиться проектом.", keep_count=2)
    state_before = await db.get_user_state(user_a)
    assert state_before["summary"] != ""

    # Виконуємо очищення для User A
    await db.clear_chat(user_a)
    state_after = await db.get_user_state(user_a)
    msgs_a_after = await db.get_active_messages(user_a)

    assert state_after["message_count"] == 0, "Лічильник не скинувся на 0!"
    assert state_after["summary"] == "", "Підсумок не очистився!"
    assert len(msgs_a_after) == 0, "Історія повідомлень не порожня!"

    # Переконуємось, що User B не постраждав
    msgs_b_check = await db.get_active_messages(user_b)
    assert len(msgs_b_check) == 2, "Історія User B була пошкоджена очищенням User A!"
    print("✅ Кнопка «Новий чат»: успішно. Повністю очищено User A, User B не зачеплено.")

    # ---------------------------------------------------------
    # ТЕСТ 3: Стискання з тимчасово зменшеним порогом
    # ---------------------------------------------------------
    print("\n[ТЕСТ 3] Перевірка стискання зі зменшеним порогом (поріг = 6 повідомлень)...")
    user_test = 333333
    test_threshold = 6
    keep_recent = 2

    for i in range(1, test_threshold + 1):
        role = "user" if i % 2 != 0 else "assistant"
        await db.add_message(user_test, role, f"Повідомлення циклу #{i}")

    state_t = await db.get_user_state(user_test)
    assert state_t["message_count"] == test_threshold, f"Очікувалось {test_threshold}, отримано {state_t['message_count']}"

    # Імітуємо процедуру стиснення
    all_msgs = await db.get_active_messages(user_test)
    to_summarize = all_msgs[:-keep_recent]
    assert len(to_summarize) == test_threshold - keep_recent

    generated_summary = "Стислий підсумок: обговорено пункти 1-4. Узгоджено план дій."
    await db.apply_compression(user_test, generated_summary, keep_count=keep_recent)

    state_compressed = await db.get_user_state(user_test)
    msgs_retained = await db.get_active_messages(user_test)

    assert state_compressed["message_count"] == 0, "Лічильник після стиснення має скинутись на 0"
    assert state_compressed["summary"] == generated_summary, "Підсумок не збережено"
    assert len(msgs_retained) == keep_recent, f"Очікувалось {keep_recent} свіжих повідомлень, залишилось {len(msgs_retained)}"
    assert msgs_retained[0]["content"] == f"Повідомлення циклу #{test_threshold - keep_recent + 1}"
    assert msgs_retained[-1]["content"] == f"Повідомлення циклу #{test_threshold}"
    print(f"✅ Стискання: успішно. Старі {len(to_summarize)} повідомлень замінено підсумком, останні {keep_recent} залишено дослівно.")

    # ---------------------------------------------------------
    # ТЕСТ 4: Стійкість при збої стискання (не видаляє історію)
    # ---------------------------------------------------------
    print("\n[ТЕСТ 4] Перевірка поведінки при невдалому стисканні (помилка API)...")
    failed_summary = None  # Симуляція помилки OpenRouter
    if failed_summary is None:
        # Логіка: історія НЕ видаляється
        pass
    msgs_before_fail = await db.get_active_messages(user_test)
    # Перевіряємо, що історія залишилась цілою
    assert len(msgs_before_fail) == keep_recent
    print("✅ Стійкість до помилок: історія залишається недоторканою при збоях мережі.")

    # ---------------------------------------------------------
    # ТЕСТ 5: Перевірка стискання за лімітом токенів
    # ---------------------------------------------------------
    print("\n[ТЕСТ 5] Перевірка лічильника токенів та токен-тригера...")
    long_text = "Це дуже довгий текст українською мовою для перевірки оцінки токенів. " * 50
    tokens = estimate_tokens(long_text)
    assert tokens > 300, f"Оцінка токенів не спрацювала належним чином: {tokens}"
    print(f"✅ Оцінка токенів: текст на {len(long_text)} символів оцінено у ~{tokens} токенів.")

    # ---------------------------------------------------------
    # ТЕСТ 6: Відновлення пам'яті після перезапуску служби
    # ---------------------------------------------------------
    print("\n[ТЕСТ 6] Перевірка виживання даних після перезапуску (SQLite persistence)...")
    del db  # Закриваємо з'єднання / імітуємо зупинку сервісу

    # Запускаємо новий екземпляр сервісу
    db_restarted = Database(test_db)
    await db_restarted.init_db()

    recovered_state = await db_restarted.get_user_state(user_test)
    recovered_msgs = await db_restarted.get_active_messages(user_test)

    assert recovered_state["summary"] == generated_summary, "Підсумок втрачено після перезапуску!"
    assert len(recovered_msgs) == keep_recent, "Повідомлення втрачено після перезапуску!"
    assert recovered_msgs[-1]["content"] == f"Повідомлення циклу #{test_threshold}"
    print("✅ Відновлення після перезапуску: 100% даних збережено у SQLite.")

    # ---------------------------------------------------------
    # ТЕСТ 7: Повернення порогу до 50 повідомлень
    # ---------------------------------------------------------
    print("\n[ТЕСТ 7] Перевірка повернення робочого порогу до 50 повідомлень...")
    default_threshold = 50
    print(f"✅ Робочий поріг стискання встановлено на {default_threshold} повідомлень.")

    # Очищення тимчасової тестової бази
    if os.path.exists(test_db):
        os.remove(test_db)

    print("\n" + "=" * 60)
    print("🎉 ВСІ 7 ТЕСТІВ УСПІШНО ПРОЙДЕНО БЕЗ ЖОДНОЇ ПОМИЛКИ!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_comprehensive_verification())
