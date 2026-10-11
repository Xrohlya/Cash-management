import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from aiogram.exceptions import TelegramBadRequest
from aiogram.methods import EditMessageText
from backend.notifications import refresh_telegram_status


class NotificationTests(unittest.IsolatedAsyncioTestCase):
    async def test_document_is_replaced_with_text_and_reference_is_saved(self):
        method = EditMessageText(chat_id=101, message_id=5, text="Budget")
        sent = SimpleNamespace(chat=SimpleNamespace(id=101), message_id=6)
        bot = SimpleNamespace(
            edit_message_text=AsyncMock(side_effect=TelegramBadRequest(method, "there is no text in the message to edit")),
            send_message=AsyncMock(return_value=sent), delete_message=AsyncMock(),
            session=SimpleNamespace(close=AsyncMock()),
        )
        with patch("config.settings.BOT_TOKEN", "test"), patch("aiogram.Bot", return_value=bot), patch("database.repository.get_status_message", return_value=(101, 5)), patch("database.repository.set_status_message") as save, patch("services.budget.status", return_value="Budget"):
            await refresh_telegram_status(101)
        save.assert_called_once_with(101, 101, 6)
        bot.send_message.assert_awaited_once()
        bot.delete_message.assert_awaited_once_with(101, 5)
        bot.session.close.assert_awaited_once()
