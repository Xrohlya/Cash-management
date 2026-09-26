import asyncio
import logging

from aiogram.types import BotCommand, MenuButtonCommands, MenuButtonWebApp, WebAppInfo

from bot.connection import create_bot, create_dispatcher
from bot.handlers import router
from config.settings import WEBAPP_URL
from database.db import init_db
from database.repository import (
    apply_due_recurring_payments,
    due_recurring_notifications,
    mark_recurring_notified,
)


async def recurring_notification_loop(bot):
    while True:
        try:
            for payment in due_recurring_notifications():
                await bot.send_message(
                    payment["user_id"],
                    "🔁 <b>Регулярный платёж сегодня</b>\n\n"
                    f"Нужно оплатить: <b>{payment['title']}</b>\n"
                    f"Сумма: <b>{payment['amount']:,.0f} ₽</b>\n\n"
                    "Сумма будет учтена в бюджете отдельно от обычных расходов.",
                    parse_mode="HTML",
                )
                mark_recurring_notified(payment["id"])
                apply_due_recurring_payments(payment["user_id"])
        except Exception:
            logging.exception("Recurring payment notification failed")
        await asyncio.sleep(3600)


async def configure_bot(bot):
    await bot.set_my_commands([
        BotCommand(command="start", description="Открыть бюджет"),
        BotCommand(command="status", description="Текущее состояние"),
        BotCommand(command="history", description="Последние операции"),
        BotCommand(command="help", description="Помощь"),
    ])
    if WEBAPP_URL:
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(text="Бюджет", web_app=WebAppInfo(url=WEBAPP_URL))
        )
    else:
        await bot.set_chat_menu_button(menu_button=MenuButtonCommands())


async def main():
    logging.basicConfig(level=logging.INFO)
    init_db()
    bot = create_bot()
    await configure_bot(bot)
    dp = create_dispatcher()
    dp.include_router(router)
    logging.info("Cash Management bot started")
    notification_task = asyncio.create_task(recurring_notification_loop(bot))
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        notification_task.cancel()


if __name__ == "__main__":
    asyncio.run(main())
