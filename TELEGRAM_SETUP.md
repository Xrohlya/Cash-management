# Cash Management — Telegram Mini App

Mini App: https://xrohlya.github.io/Cash-management/

## Подключение к Telegram-боту

В aiogram 3 добавьте кнопку:

    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

    button = InlineKeyboardButton(text="📱 Cash Management", web_app=WebAppInfo(url="https://xrohlya.github.io/Cash-management/"))
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[button]])

## Передача данных

Mini App отправляет JSON через Telegram WebApp API:

    {"type":"expense","amount":2500,"description":"продукты"}
    {"type":"income","amount":200000}
    {"type":"save","amount":30000}
    {"type":"analytics"}
    {"type":"today"}
    {"type":"report"}

На стороне бота обработайте web_app_data. Для финансовых операций всегда используйте message.from_user.id, а не user_id из JSON.

Пример:

    import json
    from aiogram import F

    @router.message(F.web_app_data)
    async def miniapp_data(message: Message):
        data = json.loads(message.web_app_data.data)
        user_id = message.from_user.id
        kind = data.get("type")
        if kind == "expense":
            add_expense(user_id, float(data["amount"]), data.get("description") or "Расход")
        elif kind == "income":
            add_income(user_id, float(data["amount"]))
        elif kind == "save":
            add_to_savings(user_id, float(data["amount"]))

## GitHub Pages

Repository → Settings → Pages → Build and deployment → Deploy from a branch → main → /(root) → Save.

## Архитектура

GitHub Pages содержит только интерфейс. SQLite, токен и config/access.py остаются на компьютере с ботом. Новая база для Mini App не создаётся.
