from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from config.settings import WEBAPP_URL


def main_menu():
    rows = []
    if WEBAPP_URL:
        rows.append([
            InlineKeyboardButton(
                text="Открыть приложение",
                web_app=WebAppInfo(url=WEBAPP_URL),
            )
        ])
    rows.extend([
        [InlineKeyboardButton(text="💳 Бюджет", callback_data="status"), InlineKeyboardButton(text="📆 Сегодня", callback_data="today")],
        [InlineKeyboardButton(text="📋 История", callback_data="history"), InlineKeyboardButton(text="📈 Прогноз", callback_data="forecast")],
        [InlineKeyboardButton(text="🏦 Накопления", callback_data="savings"), InlineKeyboardButton(text="🎯 Цель", callback_data="goal")],
        [InlineKeyboardButton(text="🔁 Регулярные платежи", callback_data="recurring"), InlineKeyboardButton(text="💼 Источники дохода", callback_data="income_sources")],
        [InlineKeyboardButton(text="📊 Аналитика", callback_data="analytics"), InlineKeyboardButton(text="📊 Сравнение", callback_data="compare")],
        [InlineKeyboardButton(text="❓ Помощь", callback_data="help"), InlineKeyboardButton(text="🧹 Очистить чат", callback_data="clear_chat")],
        [InlineKeyboardButton(text="📄 PDF / Excel", callback_data="report"), InlineKeyboardButton(text="↻ Обновить", callback_data="status")],
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def confirm_keyboard(confirm_data: str, cancel_data: str = "cancel"):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Подтвердить", callback_data=confirm_data),
        InlineKeyboardButton(text="❌ Отмена", callback_data=cancel_data),
    ]])
