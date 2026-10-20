import asyncio
import logging

from aiogram.client.session.middlewares.base import BaseRequestMiddleware
from aiogram.exceptions import TelegramRetryAfter, TelegramNetworkError, TelegramServerError
from aiogram.methods import GetUpdates
from aiogram.utils.backoff import BackoffConfig
from services.connection_status import ConnectionStatus


POLLING_BACKOFF = BackoffConfig(
    min_delay=2.0, max_delay=30.0, factor=1.7, jitter=0.2,
)
logger = logging.getLogger(__name__)


class PollingRateLimitMiddleware(BaseRequestMiddleware):
    def __init__(self):
        self.connection = ConnectionStatus("Telegram API")

    async def __call__(self, make_request, bot, method):
        if not isinstance(method, GetUpdates):
            return await make_request(bot, method)

        while True:
            try:
                result = await make_request(bot, method)
                self.connection.connected()
                return result
            except (TelegramNetworkError, TelegramServerError):
                self.connection.failed()
                raise
            except TelegramRetryAfter as error:
                delay = max(0, error.retry_after) + 1
                logger.warning(
                    "Telegram polling rate limit: waiting %s seconds", delay,
                )
                await asyncio.sleep(delay)
