"""Retry summary delivery without blocking API responses or repeating expenses."""
import asyncio
import logging

from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter
from config import settings
from database.telegram_sync import claim, finish


async def process_refresh(user_id=None):
    from backend.notifications import refresh_telegram_status

    try:
        job = await asyncio.to_thread(claim, user_id)
    except Exception:
        logging.exception("Telegram refresh queue unavailable; financial operation is not replayed")
        return False
    if job is None:
        return False
    delay = None
    try:
        delivered = await refresh_telegram_status(job["user_id"])
        if delivered is False:
            delay = 300
    except TelegramRetryAfter as exc:
        delay = max(1, exc.retry_after + 1)
        logging.warning("Telegram summary rate limited for user %s; retry in %s s", job["user_id"], delay)
    except (TelegramForbiddenError, TelegramBadRequest):
        logging.exception("Telegram rejected summary for user %s; not retrying this revision", job["user_id"])
    except Exception:
        delay = min(300, 5 * 2 ** min(job["attempts"], 6))
        logging.exception("Telegram summary delayed for user %s; retry in %s s", job["user_id"], delay)
    try:
        await asyncio.to_thread(finish, job, delay=delay)
    except Exception:
        logging.exception("Could not acknowledge Telegram refresh; lease will expire")
    return True


async def refresh_loop():
    while True:
        try:
            if settings.BOT_TOKEN and await process_refresh():
                continue
        except Exception:
            logging.exception("Telegram refresh queue unavailable; retrying later")
        await asyncio.sleep(10)
