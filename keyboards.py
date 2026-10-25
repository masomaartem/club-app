from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

def get_main_reply_keyboard() -> ReplyKeyboardMarkup:
    """Bottom persistent menu keyboard."""
    keyboard = [
        [KeyboardButton(text="📊 Загальний статус")],
        [KeyboardButton(text="🖥 Процесор"), KeyboardButton(text="🧠 Пам'ять")],
        [KeyboardButton(text="💾 Диски"), KeyboardButton(text="🌐 Мережа")],
        [KeyboardButton(text="⚡ Процеси (CPU)"), KeyboardButton(text="⚡ Процеси (RAM)")],
        [KeyboardButton(text="ℹ️ Інфо системи"), KeyboardButton(text="🔔 Сповіщення")]
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        persistent=True
    )

def get_quick_inline_keyboard(current_view: str = "summary") -> InlineKeyboardMarkup:
    """Inline navigation keyboard with instant update capability."""
    inline_keyboard = [
        [
            InlineKeyboardButton(text="🔄 Оновити дані", callback_data=f"refresh:{current_view}")
        ],
        [
            InlineKeyboardButton(text="📊 Огляд", callback_data="view:summary"),
            InlineKeyboardButton(text="🖥 CPU", callback_data="view:cpu"),
            InlineKeyboardButton(text="🧠 RAM", callback_data="view:ram")
        ],
        [
            InlineKeyboardButton(text="💾 Диски", callback_data="view:disk"),
            InlineKeyboardButton(text="🌐 Мережа", callback_data="view:net"),
            InlineKeyboardButton(text="⚡ Топ CPU", callback_data="view:top_cpu")
        ],
        [
            InlineKeyboardButton(text="⚡ Топ RAM", callback_data="view:top_ram"),
            InlineKeyboardButton(text="ℹ️ Система", callback_data="view:sys"),
            InlineKeyboardButton(text="🔔 Алерти", callback_data="view:alerts")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

def get_alerts_toggle_keyboard(alerts_enabled: bool) -> InlineKeyboardMarkup:
    """Keyboard for managing alerts."""
    status_text = "Вимкнути сповіщення 🔕" if alerts_enabled else "Увімкнути сповіщення 🔔"
    action = "disable" if alerts_enabled else "enable"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=status_text, callback_data=f"alert_toggle:{action}")],
            [InlineKeyboardButton(text="🔄 Оновити статус", callback_data="refresh:alerts")],
            [InlineKeyboardButton(text="« Назад до огляду", callback_data="view:summary")]
        ]
    )
