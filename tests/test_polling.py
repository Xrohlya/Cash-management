import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from aiogram.exceptions import TelegramRetryAfter, TelegramServerError, TelegramNetworkError
from aiogram.methods import GetUpdates, SendMessage

from bot.polling import PollingRateLimitMiddleware


class PollingTests(unittest.IsolatedAsyncioTestCase):
    async def test_lost_connection_and_recovery_are_logged_once(self):
        middleware = PollingRateLimitMiddleware()
        method = GetUpdates()
        request = AsyncMock(side_effect=[TelegramNetworkError(method, "timeout"),
                                        TelegramServerError(method, "Bad Gateway"), [], []])
        with self.assertLogs(level="INFO") as logs:
            for _ in range(2):
                with self.assertRaises((TelegramNetworkError, TelegramServerError)):
                    await middleware(request, None, method)
            await middleware(request, None, method)
            await middleware(request, None, method)
        self.assertEqual(len(logs.records), 2)
        self.assertEqual(logs.records[0].levelno, 40)
        self.assertTrue(logs.records[1].connection_restored)

    async def test_waits_for_telegram_before_retrying_same_request(self):
        method = GetUpdates(offset=42)
        request = AsyncMock(side_effect=[
            TelegramRetryAfter(method, "limited", retry_after=5),
            TelegramRetryAfter(method, "limited", retry_after=8),
            [],
        ])
        with patch("bot.polling.asyncio.sleep", new_callable=AsyncMock) as sleep:
            result = await PollingRateLimitMiddleware()(request, None, method)
        self.assertEqual(result, [])
        self.assertEqual([call.args[0] for call in sleep.await_args_list], [6, 9])
        self.assertEqual(request.await_count, 3)
        self.assertTrue(all(call.args[1] is method for call in request.await_args_list))

    async def test_sending_messages_is_not_retried(self):
        method = SendMessage(chat_id=1, text="test")
        request = AsyncMock(side_effect=TelegramRetryAfter(method, "limited", 5))
        with self.assertRaises(TelegramRetryAfter):
            await PollingRateLimitMiddleware()(request, None, method)
        self.assertEqual(request.await_count, 1)

    async def test_server_error_is_left_to_dispatcher_backoff(self):
        method = GetUpdates()
        request = AsyncMock(side_effect=TelegramServerError(method, "Bad Gateway"))
        with self.assertRaises(TelegramServerError):
            await PollingRateLimitMiddleware()(request, None, method)

    async def test_wait_can_be_cancelled(self):
        method = GetUpdates()
        request = AsyncMock(side_effect=TelegramRetryAfter(method, "limited", 5))
        with patch("bot.polling.asyncio.sleep", side_effect=asyncio.CancelledError):
            with self.assertRaises(asyncio.CancelledError):
                await PollingRateLimitMiddleware()(request, None, method)
