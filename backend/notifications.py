import asyncio
import logging
from fastapi import BackgroundTasks
from config import settings


async def refresh_telegram_status(user_id: int):
    """Send the current summary once; the persistent queue handles retries."""
    if not settings.BOT_TOKEN:
        return False
    from aiogram import Bot
    from aiogram.exceptions import TelegramBadRequest
    from bot.keyboards import main_menu
    from database.repository import get_status_message, set_status_message
    from services.budget import status

    bot = Bot(settings.BOT_TOKEN)
    try:
        saved = await asyncio.to_thread(get_status_message, user_id)
        text = await asyncio.to_thread(status, user_id)
        if saved:
            try:
                await bot.edit_message_text(
                    chat_id=saved[0], message_id=saved[1], text=text,
                    parse_mode="HTML", reply_markup=main_menu(), request_timeout=20,
                )
                return True
            except TelegramBadRequest as exc:
                message = str(exc).casefold()
                if "message is not modified" in message:
                    return True
                if not any(reason in message for reason in (
                    "message to edit not found", "message can't be edited",
                    "there is no text in the message",
                )):
                    raise
        sent = await bot.send_message(
            user_id, text, parse_mode="HTML", reply_markup=main_menu(), request_timeout=20,
        )
        await asyncio.to_thread(set_status_message, user_id, sent.chat.id, sent.message_id)
        if saved:
            try:
                await bot.delete_message(saved[0], saved[1], request_timeout=10)
            except TelegramBadRequest:
                logging.info("New summary sent; previous message cannot be deleted")
        return True
    finally:
        await bot.session.close()


def schedule_telegram_refresh(background_tasks: BackgroundTasks, user_id: int):
    from database.telegram_sync import enqueue
    from backend.sync_worker import process_refresh

    try:
        enqueue(user_id)
    except Exception:
        # The financial operation already committed: never report it as failed.
        logging.exception("Could not persist Telegram refresh for user %s", user_id)
        background_tasks.add_task(process_refresh, user_id)
        return
    background_tasks.add_task(process_refresh, user_id)
