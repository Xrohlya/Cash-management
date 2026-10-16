from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from config.settings import WEBAPP_URL, versioned_webapp_url


def main_menu():
    rows = []
    if WEBAPP_URL:
        rows.append([
            InlineKeyboardButton(
                text="Открыть приложение",
                web_app=WebAppInfo(url=versioned_webapp_url(WEBAPP_URL)),
            )
        ])
    rows.extend([
        [InlineKeyboardButton(text="💳 Бюджет", callback_data="status"), InlineKeyboardButton(text="📆 Сегодня", callback_data="today")],
        [InlineKeyboardButton(text="📋 История", callback_data="history"), InlineKeyboardButton(text="↻ Обновить", callback_data="status")],
        [InlineKeyboardButton(text="❓ Помощь", callback_data="help")],
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _section_menu(buttons):
    rows = [row for row in main_menu().inline_keyboard if any(button.web_app for button in row)]
    rows.append(buttons)
    rows.append([InlineKeyboardButton(text="‹ Бюджет", callback_data="status")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def help_menu():
    return _section_menu([InlineKeyboardButton(text="🧹 Очистить чат", callback_data="clear_chat")])


def history_menu():
    return _section_menu([
        InlineKeyboardButton(text="📄 PDF", callback_data="report"),
        InlineKeyboardButton(text="📊 Excel", callback_data="excel"),
    ])


def confirm_keyboard(confirm_data: str, cancel_data: str = "cancel"):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Подтвердить", callback_data=confirm_data),
        InlineKeyboardButton(text="❌ Отмена", callback_data=cancel_data),
    ]])
