from aiogram import Bot, Dispatcher

from config.settings import require_bot_token
from bot.polling import PollingRateLimitMiddleware


def create_bot() -> Bot:
    bot = Bot(token=require_bot_token())
    bot.session.middleware(PollingRateLimitMiddleware())
    return bot


def create_dispatcher() -> Dispatcher:
    return Dispatcher()
