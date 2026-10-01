import logging
from bot.interface import update_status, edit_interface
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message, CallbackQuery
from services.parser import parse_expense
from collections import OrderedDict

pending = {}
transient_messages = {}
answered_callbacks = OrderedDict()


async def answer_callback(callback: CallbackQuery, text=None, **kwargs):
    """Acknowledge a button press without failing on an expired Telegram query."""
    if callback.id in answered_callbacks:
        return None

    try:
        if text is None:
            result = await callback.answer(**kwargs)
        else:
            result = await callback.answer(text, **kwargs)
    except TelegramBadRequest as exc:
        error = str(exc).casefold()
        if "query is too old" not in error and "query id is invalid" not in error:
            raise
        result = None

    answered_callbacks[callback.id] = None
    if len(answered_callbacks) > 2048:
        answered_callbacks.popitem(last=False)
    return result


def set_pending(user_id: int, kind: str, amount=None, items=None):
    pending[user_id] = {"kind": kind}
    if amount is not None:
        pending[user_id]["amount"] = amount
    if items is not None:
        pending[user_id]["items"] = items


def clear_pending(user_id: int):
    return pending.pop(user_id, None)


def track_message(message: Message):
    transient_messages.setdefault(message.chat.id, set()).add(message.message_id)
    return message


def parse_expense_list(text: str):
    items = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        amount, description = parse_expense(line)
        if amount is None or amount <= 0:
            return None
        items.append((amount, description))
    return items if len(items) >= 2 else None


async def finish_callback(callback: CallbackQuery, text=None):
    user_id = callback.from_user.id
    if text is not None:
        try:
            await edit_interface(callback, text)
        except Exception:
            logging.warning("Telegram operation failed", exc_info=True)
    await update_status(callback, user_id)
    await answer_callback(callback)
