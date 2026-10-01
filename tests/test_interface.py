import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from aiogram.exceptions import TelegramBadRequest, TelegramNetworkError
from aiogram.methods import EditMessageText
from bot.interface import send_transient


class InterfaceTest(unittest.IsolatedAsyncioTestCase):
    async def test_unchanged_message_does_not_create_duplicate(self):
        method = EditMessageText(chat_id=101, message_id=5, text="Budget")
        message = SimpleNamespace(
            from_user=SimpleNamespace(id=101),
            bot=SimpleNamespace(edit_message_text=AsyncMock(
                side_effect=TelegramBadRequest(method, "message is not modified")
            )),
            answer=AsyncMock(),
        )
        with patch("bot.interface.get_status_snapshot", return_value={"status_message": (101, 5)}):
            await send_transient(message, "Budget")
        message.answer.assert_not_awaited()

    async def test_network_failure_preserves_existing_message(self):
        method = EditMessageText(chat_id=101, message_id=5, text="Budget")
        message = SimpleNamespace(
            from_user=SimpleNamespace(id=101),
            bot=SimpleNamespace(edit_message_text=AsyncMock(
                side_effect=TelegramNetworkError(method, "offline")
            )),
            answer=AsyncMock(),
        )
        with patch("bot.interface.get_status_snapshot", return_value={"status_message": (101, 5)}), patch("bot.interface.clear_status_message") as clear:
            with self.assertRaises(TelegramNetworkError):
                await send_transient(message, "Budget")
        clear.assert_not_called()
        message.answer.assert_not_awaited()
