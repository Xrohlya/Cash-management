import asyncio
import logging

from aiogram.types import BotCommand, MenuButtonCommands, MenuButtonWebApp, WebAppInfo

from bot.connection import create_bot, create_dispatcher
from bot.handlers import router
from config.settings import WEBAPP_URL
from database.db import init_db


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
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
