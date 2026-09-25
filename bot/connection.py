from aiogram import Bot, Dispatcher

from config.settings import require_bot_token


def create_bot() -> Bot:
    return Bot(token=require_bot_token())


def create_dispatcher() -> Dispatcher:
    return Dispatcher()
