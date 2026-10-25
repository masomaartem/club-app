import asyncio
import os
import shutil
from database import Database


async def run_tests():
    test_db_path = "test_data.sqlite3"
    if os.path.exists(test_db_path):
        os.remove(test_db_path)

    print("--- 1. Тестування ініціалізації БД ---")
    db = Database(test_db_path)
    await db.init_db()
    print("БД успішно створена.")

    print("\n--- 2. Тестування створення користувача ---")
    user = await db.get_or_create_user(123456)
    assert user["user_id"] == 123456
    assert user["message_count"] == 0
    assert user["summary"] == ""
    print("Користувача успішно створено з нульовим станом.")

    print("\n--- 3. Тестування додавання повідомлень ---")
    for i in range(1, 51):
        role = "user" if i % 2 != 0 else "assistant"
        count = await db.add_message(123456, role=role, content=f"Повідомлення #{i}")
        assert count == i

    state = await db.get_user_state(123456)
    print(f"Повідомлень у лічильнику: {state['message_count']}, всього в БД: {state['active_messages_count']}")
    assert state["message_count"] == 50
    assert state["active_messages_count"] == 50

    print("\n--- 4. Тестування компресії контексту ---")
    keep_count = 4
    all_msgs = await db.get_active_messages(123456)
    to_summarize = all_msgs[:-keep_count]
    assert len(to_summarize) == 46

    fake_summary = "Короткий підсумок: обговорено повідомлення від 1 до 46."
    await db.apply_compression(123456, fake_summary, keep_count)

    state_after = await db.get_user_state(123456)
    active_after = await db.get_active_messages(123456)

    print(f"Після компресії: лічильник = {state_after['message_count']}, підсумок = '{state_after['summary']}'")
    print(f"Залишено повідомлень в історії: {len(active_after)}")
    assert state_after["message_count"] == 0
    assert state_after["summary"] == fake_summary
    assert len(active_after) == 4
    assert active_after[0]["content"] == "Повідомлення #47"
    assert active_after[-1]["content"] == "Повідомлення #50"
    print("Логіка збереження останніх пар повідомлень та обрізання старих працює коректно!")

    print("\n--- 5. Тестування кнопки 'Новий чат' ---")
    await db.clear_chat(123456)
    state_cleared = await db.get_user_state(123456)
    active_cleared = await db.get_active_messages(123456)
    print(f"Після очищення: лічильник = {state_cleared['message_count']}, підсумок = '{state_cleared['summary']}', повідомлень = {len(active_cleared)}")
    assert state_cleared["message_count"] == 0
    assert state_cleared["summary"] == ""
    assert len(active_cleared) == 0
    print("Повне очищення історії, підсумку та лічильника перевірено успішно.")

    if os.path.exists(test_db_path):
        os.remove(test_db_path)
    print("\n✅ Усі тести бази даних та лічильників пройдено на 100%!")


if __name__ == "__main__":
    asyncio.run(run_tests())
