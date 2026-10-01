import asyncio
import logging
from fastapi import BackgroundTasks
from config import settings


async def refresh_telegram_status(user_id: int):
    """Refresh the persistent Telegram summary without delaying the API response."""
    if not settings.BOT_TOKEN:
        return
    from aiogram import Bot
    from aiogram.exceptions import TelegramBadRequest, TelegramNetworkError, TelegramRetryAfter
    from bot.keyboards import main_menu
    from database.repository import clear_status_message, get_status_message, set_status_message
    from services.budget import status

    bot = Bot(settings.BOT_TOKEN)
    try:
        saved = await asyncio.to_thread(get_status_message, user_id)
        text = await asyncio.to_thread(status, user_id)
        if saved:
            for attempt in range(3):
                try:
                    await bot.edit_message_text(
                        chat_id=saved[0], message_id=saved[1], text=text,
                        parse_mode="HTML", reply_markup=main_menu(),
                    )
                    break
                except (TelegramNetworkError, TelegramRetryAfter) as exc:
                    if attempt == 2:
                        raise
                    delay = getattr(exc, "retry_after", 2 * (attempt + 1))
                    if delay > 30:
                        raise
                    logging.warning("Telegram refresh retry for user %s", user_id)
                    await asyncio.sleep(delay)
                    text = await asyncio.to_thread(status, user_id)
        else:
            sent = await bot.send_message(
                user_id, text, parse_mode="HTML", reply_markup=main_menu()
            )
            await asyncio.to_thread(set_status_message, user_id, sent.chat.id, sent.message_id)
    except TelegramBadRequest as exc:
        message = str(exc).casefold()
        if "message is not modified" not in message:
            logging.warning("Mini App could not refresh Telegram summary: %s", exc)
        if "message to edit not found" in message:
            await asyncio.to_thread(clear_status_message, user_id)
            try:
                sent = await bot.send_message(
                    user_id, text, parse_mode="HTML", reply_markup=main_menu()
                )
                await asyncio.to_thread(set_status_message, user_id, sent.chat.id, sent.message_id)
            except Exception:
                logging.exception("Mini App could not recreate Telegram summary")
    except Exception:
        logging.exception("Mini App Telegram summary refresh failed")
    finally:
        await bot.session.close()


def schedule_telegram_refresh(background_tasks: BackgroundTasks, user_id: int):
    background_tasks.add_task(refresh_telegram_status, user_id)
