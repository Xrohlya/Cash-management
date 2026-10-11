import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from aiogram.exceptions import TelegramBadRequest, TelegramNetworkError
from aiogram.methods import EditMessageText
from aiogram.types import Message
from bot.interface import send_transient, update_status


class InterfaceTest(unittest.IsolatedAsyncioTestCase):
    async def test_start_sends_new_menu_before_removing_old_one(self):
        bot = SimpleNamespace(delete_message=AsyncMock())
        message = Message.model_validate({"message_id": 8, "date": 0, "chat": {"id": 101, "type": "private"}}).as_(bot)
        sent = SimpleNamespace(chat=SimpleNamespace(id=101), message_id=9)
        order = []
        async def answer(*args, **kwargs):
            order.append("send")
            return sent
        async def delete(*args):
            order.append("delete")
        bot.delete_message.side_effect = delete
        with patch("bot.interface.get_status_snapshot", return_value={"status_message": (101, 5)}), patch("bot.interface.status", return_value="Budget"), patch("bot.interface.main_menu"), patch.object(Message, "answer", side_effect=answer), patch("bot.interface.set_status_message") as save:
            await update_status(message, 101, fresh=True)
        self.assertEqual(order, ["send", "delete"])
        save.assert_called_once_with(101, 101, 9)

    async def test_start_send_failure_keeps_old_menu(self):
        bot = SimpleNamespace(delete_message=AsyncMock())
        message = Message.model_validate({"message_id": 8, "date": 0, "chat": {"id": 101, "type": "private"}}).as_(bot)
        with patch("bot.interface.get_status_snapshot", return_value={"status_message": (101, 5)}), patch("bot.interface.status", return_value="Budget"), patch("bot.interface.main_menu"), patch.object(Message, "answer", side_effect=RuntimeError("offline")), patch("bot.interface.set_status_message") as save:
            with self.assertRaises(RuntimeError):
                await update_status(message, 101, fresh=True)
        save.assert_not_called()
        bot.delete_message.assert_not_awaited()

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
