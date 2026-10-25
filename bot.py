import asyncio
import logging
import sys

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from typing import List

from aiogram import Bot, Dispatcher, F, types
from aiogram.enums import ChatType, ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    Message,
    BotCommand,
)
from aiogram.client.default import DefaultBotProperties

from config import config, mask_secret
from database import Database
from openrouter import OpenRouterClient, estimate_context_tokens

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("telegram_bot")

db = Database(config.database_path)
ai_client = OpenRouterClient()


def get_main_keyboard() -> ReplyKeyboardMarkup:
    kb = [
        [KeyboardButton(text="🔄 Новий чат"), KeyboardButton(text="📊 Статус розмови")],
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def split_text(text: str, max_chunk_size: int = 4000) -> List[str]:
    """Splits long text into chunks that fit within Telegram's 4096 character limit."""
    if len(text) <= max_chunk_size:
        return [text]

    chunks = []
    lines = text.split("\n")
    current_chunk = ""

    for line in lines:
        if len(current_chunk) + len(line) + 1 > max_chunk_size:
            if current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = ""
            while len(line) > max_chunk_size:
                chunks.append(line[:max_chunk_size])
                line = line[max_chunk_size:]
            current_chunk = line + "\n"
        else:
            current_chunk += line + "\n"

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks


async def check_and_compress_context(user_id: int) -> None:
    """
    Checks if active message counter reached the threshold OR if token count
    approaches the token limit threshold.
    If compression succeeds, saves the updated summary and preserves the last keep_count messages.
    If compression fails, preserves full history and retries later.
    """
    state = await db.get_user_state(user_id)
    message_count = state["message_count"]
    current_summary = state["summary"]
    all_messages = await db.get_active_messages(user_id)
    keep_count = config.keep_recent_messages

    # Estimate current token footprint
    estimated_tokens = estimate_context_tokens(
        system_instruction=config.system_instruction,
        summary=current_summary,
        messages=all_messages,
    )

    should_compress = False
    reason = ""

    if message_count >= config.compression_threshold:
        should_compress = True
        reason = f"лічильник повідомлень ({message_count}/{config.compression_threshold})"
    elif estimated_tokens >= config.token_trigger_threshold:
        should_compress = True
        reason = f"наближення до ліміту токенів ({estimated_tokens}/{config.token_trigger_threshold})"

    if should_compress and len(all_messages) > keep_count:
        logger.info(
            "Запуск компресії контексту для користувача %d (причина: %s)...",
            user_id,
            reason,
        )

        messages_to_summarize = all_messages[:-keep_count]

        new_summary = await ai_client.compress_context(
            previous_summary=current_summary,
            messages_to_summarize=messages_to_summarize,
        )

        if new_summary:
            await db.apply_compression(user_id, new_summary, keep_count)
            logger.info(
                "Успішна компресія для користувача %d: новий підсумок збережено, залишено %d останніх повідомлень.",
                user_id,
                keep_count,
            )
        else:
            logger.warning(
                "Стискання для користувача %d не вдалося. Повну історію збережено без видалення. Спробу буде повторено пізніше.",
                user_id,
            )


# Handlers
dp = Dispatcher()


@dp.message(F.chat.type != ChatType.PRIVATE)
async def handle_group_message(message: Message):
    """Notify users that the bot operates exclusively in direct messages."""
    await message.reply(
        "👋 Цей бот призначений для спілкування виключно в особистих повідомленнях. Напишіть мені в ПП!"
    )


@dp.message(CommandStart())
async def handle_start(message: Message):
    user_id = message.from_user.id
    await db.get_or_create_user(user_id)
    welcome_text = (
        "👋 **Вітаю!** Я ваш розумний персональний асистент на базі OpenRouter.\n\n"
        "🔹 Відповідаю виключно українською мовою.\n"
        "🔹 Зберігаю контекст нашої бесіди індивідуально для вас.\n"
        f"🔹 Автоматично стискаю старий контекст кожні {config.compression_threshold} повідомлень "
        f"або при наближенні до ліміту токенів ({config.token_trigger_threshold}).\n"
        "🔹 Натисніть кнопку **«🔄 Новий чат»**, якщо бажаєте очистити контекст і почати спочатку.\n\n"
        "Задайте своє запитання нижче! 👇"
    )
    await message.answer(
        welcome_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_main_keyboard(),
    )


@dp.message(F.text.in_({"🔄 Новий чат", "/newchat", "Новий чат"}))
async def handle_new_chat(message: Message):
    user_id = message.from_user.id
    await db.clear_chat(user_id)
    await message.answer(
        "🧹 **Новий чат розпочато!**\n\n"
        "Історію діалогу, підсумок та лічильник повідомлень повністю очищено.\n"
        "Про що поспілкуємося зараз?",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_main_keyboard(),
    )


@dp.message(F.text.in_({"📊 Статус розмови", "/status"}))
async def handle_status(message: Message):
    user_id = message.from_user.id
    state = await db.get_user_state(user_id)
    all_msgs = await db.get_active_messages(user_id)

    estimated_tokens = estimate_context_tokens(
        system_instruction=config.system_instruction,
        summary=state["summary"],
        messages=all_msgs,
    )

    has_summary = "Так (активний)" if state["summary"] else "Немає (ще не стискався)"
    summary_preview = (
        f"\n\n📝 **Поточний підсумок:**\n_{state['summary'][:300]}..._"
        if state["summary"]
        else ""
    )

    status_text = (
        "📊 **Статус поточної розмови:**\n\n"
        f"👤 Користувач: `{user_id}`\n"
        f"🤖 Модель OpenRouter: `{config.openrouter_model}`\n"
        f"💬 Повідомлень у поточному циклі: `{state['message_count']} / {config.compression_threshold}`\n"
        f"📦 Активних повідомлень у контексті: `{state['active_messages_count']}`\n"
        f"🧮 Орієнтовно токенів у контексті: `{estimated_tokens} / {config.token_trigger_threshold}`\n"
        f"🧠 Підсумок розмови: {has_summary}{summary_preview}\n\n"
        f"⚙️ Стиснення активується при досягненні {config.compression_threshold} повідомлень "
        f"або {config.token_trigger_threshold} токенів."
    )
    await message.answer(
        status_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_main_keyboard(),
    )


@dp.message(F.text)
async def handle_user_text(message: Message, bot: Bot):
    user_id = message.from_user.id
    user_text = message.text.strip()

    # 1. Store user message in history and increment counter
    await db.add_message(user_id, role="user", content=user_text)

    # 2. Show typing action in Telegram
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")

    # 3. Retrieve current context (summary + active messages)
    user_state = await db.get_user_state(user_id)
    summary = user_state["summary"]
    active_messages = await db.get_active_messages(user_id)

    # 4. Generate AI response from OpenRouter
    bot_reply = await ai_client.generate_chat_response(
        summary=summary,
        messages=active_messages,
    )

    # 5. Store assistant reply in database only if it was not an error
    if not bot_reply.startswith("⚠️"):
        await db.add_message(user_id, role="assistant", content=bot_reply)

    # 6. Send reply to user (split if longer than Telegram limit)
    chunks = split_text(bot_reply)
    for chunk in chunks:
        try:
            await message.answer(chunk, parse_mode=ParseMode.MARKDOWN, reply_markup=get_main_keyboard())
        except Exception:
            # Fallback to plain text if markdown formatting has parse errors
            await message.answer(chunk, parse_mode=None, reply_markup=get_main_keyboard())

    # 7. Check if compression threshold is reached after these messages
    await check_and_compress_context(user_id)


@dp.message()
async def handle_non_text(message: Message):
    """Handle non-text messages like photos, stickers, voices."""
    await message.answer(
        "📝 Я обробляю лише текстові повідомлення. Будь ласка, надішліть ваше запитання текстом.",
        reply_markup=get_main_keyboard(),
    )


async def set_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Запустити бота"),
        BotCommand(command="newchat", description="Очистити історію та почати новий чат"),
        BotCommand(command="status", description="Переглянути статус контексту та лічильника"),
    ]
    await bot.set_my_commands(commands)


async def main():
    config.validate()
    await db.init_db()

    logger.info("Конфігурація успішно перевірена. Модель: %s", config.openrouter_model)
    logger.info("OpenRouter ключ: %s", mask_secret(config.openrouter_api_key))
    logger.info("Telegram токен: %s", mask_secret(config.telegram_bot_token))

    bot = Bot(
        token=config.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
    )

    await set_bot_commands(bot)
    logger.info("Бот успішно запущений і готовий приймати повідомлення!")

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот зупинений.")
