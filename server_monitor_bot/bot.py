import asyncio
import logging
import time
import sys
from typing import Dict

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery, BotCommand
from aiogram.exceptions import TelegramBadRequest

import config
import monitor
import keyboards

# Setup logging
log_file = config.BASE_DIR / "bot.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_file, encoding="utf-8")
    ]
)
logger = logging.getLogger("server_monitor_bot")

bot = Bot(
    token=config.BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

# Memory cache for active alerts cooldown: {alert_key: last_sent_timestamp}
last_alert_sent: Dict[str, float] = {}
active_alerts_state: Dict[str, bool] = {}


def check_auth(user_id: int) -> bool:
    """Check if user has access. If no admins exist, register first user."""
    admins = config.load_admins()
    if not admins:
        config.add_admin(user_id)
        logger.info(f"Перший користувач {user_id} автоматично призначений головним адміністратором.")
        return True
    return user_id in admins


def render_view(view: str) -> tuple[str, any]:
    """Return text and inline keyboard for a specific view."""
    if view == "cpu":
        return monitor.get_cpu_details(), keyboards.get_quick_inline_keyboard("cpu")
    elif view == "ram":
        return monitor.get_ram_details(), keyboards.get_quick_inline_keyboard("ram")
    elif view == "disk":
        return monitor.get_disk_details(), keyboards.get_quick_inline_keyboard("disk")
    elif view == "net":
        return monitor.get_network_details(), keyboards.get_quick_inline_keyboard("net")
    elif view == "top_cpu":
        return monitor.get_processes_text("cpu", 10), keyboards.get_quick_inline_keyboard("top_cpu")
    elif view == "top_ram":
        return monitor.get_processes_text("ram", 10), keyboards.get_quick_inline_keyboard("top_ram")
    elif view == "sys":
        return monitor.get_system_info(), keyboards.get_quick_inline_keyboard("sys")
    elif view == "alerts":
        settings = config.load_settings()
        status_text = "🟢 УВІМКНЕНО" if settings.get("alerts_enabled") else "🔴 ВИМКНЕНО"
        text = (
            f"🔔 <b>НАЛАШТУВАННЯ АВТОМАТИЧНИХ СПОВІЩЕНЬ</b>\n"
            f"<code>────────────────────────</code>\n"
            f"• Статус сповіщень: <b>{status_text}</b>\n"
            f"• Поріг CPU: <b>{settings.get('alert_cpu_threshold')}%</b>\n"
            f"• Поріг RAM: <b>{settings.get('alert_ram_threshold')}%</b>\n"
            f"• Поріг Диска: <b>{settings.get('alert_disk_threshold')}%</b>\n"
            f"• Інтервал перевірки: <b>{settings.get('alert_interval_seconds')} сек.</b>\n"
            f"• Кулдаун сповіщень: <b>{settings.get('alert_cooldown_minutes')} хв.</b>\n\n"
            f"<i>Бот постійно у фоні аналізує сервер та миттєво повідомить у разі критичного перевантаження.</i>"
        )
        return text, keyboards.get_alerts_toggle_keyboard(settings.get("alerts_enabled", True))
    else:  # summary default
        return monitor.get_summary(), keyboards.get_quick_inline_keyboard("summary")


# --- COMMAND HANDLERS ---

@dp.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id
    user_name = message.from_user.full_name
    
    admins = config.load_admins()
    if not admins:
        config.add_admin(user_id)
        welcome_prefix = f"🎉 <b>Вітаємо, {user_name}!</b>\nВи автоматично зареєстровані як власник та адміністратор моніторингу цього сервера.\n\n"
    elif user_id not in admins:
        await message.answer(
            f"⛔ <b>Доступ обмежено!</b>\n\n"
            f"Цей бот моніторить приватний сервер.\n"
            f"Ваш Telegram ID: <code>{user_id}</code>\n\n"
            f"Для отримання доступу передайте цей ID власнику сервера, щоб він виконав:\n"
            f"<code>/add_admin {user_id}</code>"
        )
        return
    else:
        welcome_prefix = f"👋 <b>З поверненням, {user_name}!</b>\n\n"

    text, kb = render_view("summary")
    await message.answer(
        welcome_prefix + text,
        reply_markup=keyboards.get_main_reply_keyboard()
    )


@dp.message(Command("help"))
async def cmd_help(message: Message):
    if not check_auth(message.from_user.id):
        return
    help_text = (
        f"🤖 <b>КОМАНДИ БОТА МОНІТОРИНГУ СЕРВЕРА</b>\n"
        f"<code>────────────────────────</code>\n"
        f"📊 /status - Загальний огляд стану сервера\n"
        f"🖥 /cpu - Детальний аналіз процесора\n"
        f"🧠 /ram - Стан оперативної пам'яті та swap\n"
        f"💾 /disk - Аналіз накопичувачів та розділів\n"
        f"🌐 /net - Мережевий трафік та інтерфейси\n"
        f"⚡ /top - Топ процесів за навантаженням CPU\n"
        f"⚡ /top_ram - Топ процесів за пам'яттю RAM\n"
        f"ℹ️ /sys - Дані про ОС, запуск та користувачів\n"
        f"🔔 /alerts - Стан автоматичних сповіщень\n\n"
        f"<b>Адміністрування:</b>\n"
        f"• <code>/add_admin &lt;id&gt;</code> - Надати доступ користувачу\n"
        f"• <code>/del_admin &lt;id&gt;</code> - Забрати доступ\n"
        f"• <code>/admins</code> - Список адміністраторів\n"
        f"<code>────────────────────────</code>\n"
        f"<i>Ви також можете користуватись кнопками під полем вводу або під повідомленням.</i>"
    )
    await message.answer(help_text)


@dp.message(Command("status"))
async def cmd_status(message: Message):
    if not check_auth(message.from_user.id):
        return
    text, kb = render_view("summary")
    await message.answer(text, reply_markup=kb)


@dp.message(Command("cpu"))
async def cmd_cpu(message: Message):
    if not check_auth(message.from_user.id):
        return
    text, kb = render_view("cpu")
    await message.answer(text, reply_markup=kb)


@dp.message(Command("ram"))
async def cmd_ram(message: Message):
    if not check_auth(message.from_user.id):
        return
    text, kb = render_view("ram")
    await message.answer(text, reply_markup=kb)


@dp.message(Command("disk"))
async def cmd_disk(message: Message):
    if not check_auth(message.from_user.id):
        return
    text, kb = render_view("disk")
    await message.answer(text, reply_markup=kb)


@dp.message(Command("net"))
async def cmd_net(message: Message):
    if not check_auth(message.from_user.id):
        return
    text, kb = render_view("net")
    await message.answer(text, reply_markup=kb)


@dp.message(Command("top"))
async def cmd_top(message: Message):
    if not check_auth(message.from_user.id):
        return
    text, kb = render_view("top_cpu")
    await message.answer(text, reply_markup=kb)


@dp.message(Command("top_ram"))
async def cmd_top_ram(message: Message):
    if not check_auth(message.from_user.id):
        return
    text, kb = render_view("top_ram")
    await message.answer(text, reply_markup=kb)


@dp.message(Command("sys"))
async def cmd_sys(message: Message):
    if not check_auth(message.from_user.id):
        return
    text, kb = render_view("sys")
    await message.answer(text, reply_markup=kb)


@dp.message(Command("alerts"))
async def cmd_alerts(message: Message):
    if not check_auth(message.from_user.id):
        return
    text, kb = render_view("alerts")
    await message.answer(text, reply_markup=kb)


# --- ADMIN COMMANDS ---

@dp.message(Command("add_admin"))
async def cmd_add_admin(message: Message):
    if not check_auth(message.from_user.id):
        return
    parts = message.text.strip().split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("⚠️ Вкажіть числовий Telegram ID:\nНаприклад: <code>/add_admin 123456789</code>")
        return
    target_id = int(parts[1])
    config.add_admin(target_id)
    await message.answer(f"✅ Користувача з ID <code>{target_id}</code> додано до адміністраторів.")


@dp.message(Command("del_admin"))
async def cmd_del_admin(message: Message):
    if not check_auth(message.from_user.id):
        return
    parts = message.text.strip().split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("⚠️ Вкажіть числовий Telegram ID:\nНаприклад: <code>/del_admin 123456789</code>")
        return
    target_id = int(parts[1])
    if target_id == message.from_user.id:
        await message.answer("❌ Ви не можете видалити самі себе.")
        return
    config.remove_admin(target_id)
    await message.answer(f"🗑 Користувача <code>{target_id}</code> видалено зі списку адміністраторів.")


@dp.message(Command("admins"))
async def cmd_admins(message: Message):
    if not check_auth(message.from_user.id):
        return
    admins = config.load_admins()
    lines = ["👥 <b>СПИСОК АДМІНІСТРАТОРІВ</b>", "<code>────────────────────────</code>"]
    for adm in admins:
        mark = " (Ви)" if adm == message.from_user.id else ""
        lines.append(f"• ID: <code>{adm}</code>{mark}")
    await message.answer("\n".join(lines))


# --- REPLY BUTTONS ROUTING ---

@dp.message(F.text == "📊 Загальний статус")
async def btn_summary(message: Message):
    if not check_auth(message.from_user.id):
        return
    text, kb = render_view("summary")
    await message.answer(text, reply_markup=kb)


@dp.message(F.text == "🖥 Процесор")
async def btn_cpu(message: Message):
    if not check_auth(message.from_user.id):
        return
    text, kb = render_view("cpu")
    await message.answer(text, reply_markup=kb)


@dp.message(F.text == "🧠 Пам'ять")
async def btn_ram(message: Message):
    if not check_auth(message.from_user.id):
        return
    text, kb = render_view("ram")
    await message.answer(text, reply_markup=kb)


@dp.message(F.text == "💾 Диски")
async def btn_disk(message: Message):
    if not check_auth(message.from_user.id):
        return
    text, kb = render_view("disk")
    await message.answer(text, reply_markup=kb)


@dp.message(F.text == "🌐 Мережа")
async def btn_net(message: Message):
    if not check_auth(message.from_user.id):
        return
    text, kb = render_view("net")
    await message.answer(text, reply_markup=kb)


@dp.message(F.text == "⚡ Процеси (CPU)")
async def btn_top_cpu(message: Message):
    if not check_auth(message.from_user.id):
        return
    text, kb = render_view("top_cpu")
    await message.answer(text, reply_markup=kb)


@dp.message(F.text == "⚡ Процеси (RAM)")
async def btn_top_ram(message: Message):
    if not check_auth(message.from_user.id):
        return
    text, kb = render_view("top_ram")
    await message.answer(text, reply_markup=kb)


@dp.message(F.text == "ℹ️ Інфо системи")
async def btn_sys(message: Message):
    if not check_auth(message.from_user.id):
        return
    text, kb = render_view("sys")
    await message.answer(text, reply_markup=kb)


@dp.message(F.text == "🔔 Сповіщення")
async def btn_alerts(message: Message):
    if not check_auth(message.from_user.id):
        return
    text, kb = render_view("alerts")
    await message.answer(text, reply_markup=kb)


@dp.message()
async def default_message_handler(message: Message):
    if not check_auth(message.from_user.id):
        await message.answer(
            f"⛔ <b>Доступ обмежено!</b>\n\n"
            f"Ваш Telegram ID: <code>{message.from_user.id}</code>\n"
            f"Зверніться до адміністратора сервера."
        )
        return
    text, kb = render_view("summary")
    await message.answer(text, reply_markup=keyboards.get_main_reply_keyboard())


# --- INLINE CALLBACK QUERY HANDLERS ---

@dp.callback_query(F.data.startswith("view:"))
async def callback_view(query: CallbackQuery):
    if not check_auth(query.from_user.id):
        await query.answer("Немає доступу", show_alert=True)
        return
    view = query.data.split(":", 1)[1]
    text, kb = render_view(view)
    try:
        await query.message.edit_text(text, reply_markup=kb)
        await query.answer()
    except TelegramBadRequest:
        await query.answer()


@dp.callback_query(F.data.startswith("refresh:"))
async def callback_refresh(query: CallbackQuery):
    if not check_auth(query.from_user.id):
        await query.answer("Немає доступу", show_alert=True)
        return
    view = query.data.split(":", 1)[1]
    text, kb = render_view(view)
    try:
        await query.message.edit_text(text, reply_markup=kb)
        await query.answer("✅ Дані оновлено!")
    except TelegramBadRequest:
        await query.answer("ℹ️ Змін у даних немає")


@dp.callback_query(F.data.startswith("alert_toggle:"))
async def callback_alert_toggle(query: CallbackQuery):
    if not check_auth(query.from_user.id):
        await query.answer("Немає доступу", show_alert=True)
        return
    action = query.data.split(":", 1)[1]
    settings = config.load_settings()
    settings["alerts_enabled"] = (action == "enable")
    config.save_settings(settings)
    
    text, kb = render_view("alerts")
    try:
        await query.message.edit_text(text, reply_markup=kb)
    except TelegramBadRequest:
        pass
    status_str = "увімкнено" if settings["alerts_enabled"] else "вимкнено"
    await query.answer(f"Сповіщення {status_str}!")


# --- BACKGROUND MONITORING TASK ---

async def background_monitoring_loop():
    """Periodically check server thresholds and alert admins."""
    logger.info("Фоновий моніторинг запущено.")
    while True:
        try:
            settings = config.load_settings()
            if settings.get("alerts_enabled", True):
                cooldown_sec = settings.get("alert_cooldown_minutes", 15) * 60
                now = time.time()
                
                # Check metrics
                alerts = monitor.check_alerts(settings)
                admins = config.load_admins()
                
                if alerts and admins:
                    for alert_msg in alerts:
                        alert_key = alert_msg.split('\n')[0]
                        last_sent = last_alert_sent.get(alert_key, 0)
                        
                        if (now - last_sent) >= cooldown_sec:
                            last_alert_sent[alert_key] = now
                            active_alerts_state[alert_key] = True
                            
                            full_msg = f"🚨 <b>СИСТЕМНЕ СПОВІЩЕННЯ!</b>\n<code>────────────────────────</code>\n{alert_msg}"
                            for admin_id in admins:
                                try:
                                    await bot.send_message(admin_id, full_msg)
                                except Exception as err:
                                    logger.error(f"Помилка відправки сповіщення адміну {admin_id}: {err}")
                elif not alerts and active_alerts_state:
                    # Send recovery notice if any previous alert was active
                    if any(active_alerts_state.values()) and admins:
                        recovery_msg = (
                            "✅ <b>Всі показники сервера повернулися до норми!</b>\n"
                            "<code>────────────────────────</code>\n"
                            "Навантаження стабілізовано."
                        )
                        for admin_id in admins:
                            try:
                                await bot.send_message(admin_id, recovery_msg)
                            except Exception:
                                pass
                        active_alerts_state.clear()
                        
            interval = settings.get("alert_interval_seconds", 60)
            await asyncio.sleep(interval)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Помилка у циклі моніторингу: {e}", exc_info=True)
            await asyncio.sleep(30)


async def set_bot_commands():
    """Register bot menu commands in Telegram UI."""
    commands = [
        BotCommand(command="status", description="Загальний статус сервера"),
        BotCommand(command="cpu", description="Навантаження процесора"),
        BotCommand(command="ram", description="Використання пам'яті"),
        BotCommand(command="disk", description="Дисковий простір"),
        BotCommand(command="net", description="Мережева статистика"),
        BotCommand(command="top", description="Топ процесів (CPU)"),
        BotCommand(command="top_ram", description="Топ процесів (RAM)"),
        BotCommand(command="sys", description="Інформація про систему"),
        BotCommand(command="alerts", description="Налаштування сповіщень"),
        BotCommand(command="help", description="Довідка по командах"),
    ]
    try:
        await bot.set_my_commands(commands)
    except Exception as e:
        logger.warning(f"Не вдалося встановити команди бота: {e}")


async def main():
    logger.info("Запуск Telegram-бота моніторингу сервера...")
    await set_bot_commands()
    
    # Run background alerting task
    alert_task = asyncio.create_task(background_monitoring_loop())
    
    try:
        # Delete webhook if any was set, and start polling
        await bot.delete_webhook(drop_pending_updates=False)
        await dp.start_polling(bot)
    finally:
        alert_task.cancel()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
