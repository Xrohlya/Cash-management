import asyncio
import logging
from html import escape

from aiogram.types import BotCommand, MenuButtonCommands, MenuButtonWebApp, WebAppInfo

from bot.connection import create_bot, create_dispatcher
from bot.console import ActivityMiddleware, configure_logging, show_startup
from bot.handlers import router
from bot.keyboards import main_menu
from config.settings import DATABASE_URL, WEBAPP_URL, versioned_webapp_url
from database.db import close_db_pool, init_db
from database.repository import (
    apply_due_recurring_payments,
    due_recurring_notifications,
    mark_recurring_notified,
    clear_status_message,
    get_status_message,
    get_status_snapshot,
    list_user_summaries,
    set_status_message,
)
from services.budget import money, status


async def show_recurring_notice(bot, payment):
    user_id = int(payment["user_id"])
    apply_due_recurring_payments(user_id)
    notice = (
        "🔁 <b>ПЛАТЁЖ СЕГОДНЯ</b>\n"
        f"{escape(payment['title'])} · <b>{money(float(payment['amount']))} ₽</b>\n"
        "Учтён отдельно от обычных расходов.\n\n"
    )
    text = notice + status(user_id, get_status_snapshot(user_id))
    saved = get_status_message(user_id)
    if saved:
        try:
            await bot.edit_message_text(
                chat_id=saved[0], message_id=saved[1], text=text,
                parse_mode="HTML", reply_markup=main_menu(),
            )
            return
        except Exception:
            clear_status_message(user_id)
    sent = await bot.send_message(
        user_id, text, parse_mode="HTML", reply_markup=main_menu()
    )
    set_status_message(user_id, sent.chat.id, sent.message_id)


async def recurring_notification_loop(bot):
    while True:
        retry_delay = 3600
        try:
            for payment in due_recurring_notifications():
                await show_recurring_notice(bot, payment)
                mark_recurring_notified(payment["id"])
        except Exception:
            logging.exception("Recurring payment notification failed")
            retry_delay = 60
        await asyncio.sleep(retry_delay)


async def configure_bot(bot):
    await bot.set_my_commands([
        BotCommand(command="start", description="Открыть бюджет"),
        BotCommand(command="status", description="Текущее состояние"),
        BotCommand(command="history", description="Последние операции"),
        BotCommand(command="sources", description="Источники дохода"),
        BotCommand(command="help", description="Помощь"),
    ])
    if WEBAPP_URL:
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="Бюджет", web_app=WebAppInfo(url=versioned_webapp_url(WEBAPP_URL))
            )
        )
    else:
        await bot.set_chat_menu_button(menu_button=MenuButtonCommands())


async def main():
    configure_logging()
    init_db()
    bot = create_bot()
    bot_info = await bot.get_me()
    await configure_bot(bot)
    dp = create_dispatcher()
    dp.message.outer_middleware(ActivityMiddleware())
    dp.callback_query.outer_middleware(ActivityMiddleware())
    dp.include_router(router)
    users = list_user_summaries()
    database_name = "PostgreSQL · Aiven" if DATABASE_URL else "SQLite · локальная"
    show_startup(bot_info, users, database_name)
    notification_task = asyncio.create_task(recurring_notification_loop(bot))
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        notification_task.cancel()
        close_db_pool()
        print("\nБот остановлен.")


if __name__ == "__main__":
    asyncio.run(main())
