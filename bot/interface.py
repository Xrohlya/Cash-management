import logging
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message, CallbackQuery, FSInputFile
from bot.keyboards import main_menu
from database.repository import get_status_snapshot, get_status_message, set_status_message, clear_status_message
from services.budget import status


def _can_replace(exc):
    error = str(exc).casefold()
    if "message is not modified" in error:
        return False
    if "message to edit not found" in error or "message can't be edited" in error or "there is no text in the message" in error:
        logging.info("Replacing unavailable Telegram interface: %s", exc)
        return True
    raise exc

async def send_transient(message: Message, text: str, **kwargs):
    """Show temporary-looking text by editing the ONE persistent bot message."""
    user_id = message.from_user.id
    snapshot = get_status_snapshot(user_id)
    saved = snapshot["status_message"]
    parse_mode = kwargs.pop("parse_mode", "HTML")
    reply_markup = kwargs.pop("reply_markup", main_menu())

    if saved:
        chat_id, message_id = saved
        try:
            await message.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                parse_mode=parse_mode,
                reply_markup=reply_markup,
            )
            return message.bot
        except TelegramBadRequest as exc:
            if not _can_replace(exc):
                return
            try:
                await message.bot.delete_message(chat_id, message_id)
            except Exception:
                logging.warning("Telegram operation failed", exc_info=True)
            clear_status_message(user_id)

    sent = await message.answer(text, parse_mode=parse_mode, reply_markup=reply_markup)
    set_status_message(user_id, sent.chat.id, sent.message_id)
    return sent


async def update_status(message_or_callback, user_id: int):
    """Keep one persistent status message per user and update it in place."""
    snapshot = get_status_snapshot(user_id)
    text = status(user_id, snapshot)
    markup = main_menu()
    saved = snapshot["status_message"]

    if saved:
        chat_id, message_id = saved
        try:
            bot = message_or_callback.bot
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                parse_mode="HTML",
                reply_markup=markup,
            )
            if isinstance(message_or_callback, CallbackQuery):
                source = message_or_callback.message
                if source and (source.chat.id, source.message_id) != saved:
                    try:
                        await source.delete()
                    except Exception:
                        logging.warning("Telegram operation failed", exc_info=True)
            return
        except TelegramBadRequest as exc:
            if not _can_replace(exc):
                return
            # Сообщение могли удалить вручную или Telegram больше не даёт его редактировать.
            if saved:
                try:
                    await message_or_callback.bot.delete_message(saved[0], saved[1])
                except Exception:
                    logging.warning("Telegram operation failed", exc_info=True)
            clear_status_message(user_id)

    if isinstance(message_or_callback, CallbackQuery):
        sent = await message_or_callback.message.answer(text, parse_mode="HTML", reply_markup=markup)
    else:
        sent = await message_or_callback.answer(text, parse_mode="HTML", reply_markup=markup)
    set_status_message(user_id, sent.chat.id, sent.message_id)


async def edit_interface(callback: CallbackQuery, text: str, reply_markup=None):
    """Edit the user's one persistent interface message, even from an old button."""
    user_id = callback.from_user.id
    snapshot = get_status_snapshot(user_id)
    markup = reply_markup or main_menu()
    saved = snapshot["status_message"]
    if saved:
        try:
            await callback.bot.edit_message_text(
                chat_id=saved[0], message_id=saved[1], text=text,
                parse_mode="HTML", reply_markup=markup,
            )
            if callback.message and (callback.message.chat.id, callback.message.message_id) != saved:
                try:
                    await callback.message.delete()
                except Exception:
                    logging.warning("Telegram operation failed", exc_info=True)
            return
        except TelegramBadRequest as exc:
            if not _can_replace(exc):
                return
            try:
                await callback.bot.delete_message(saved[0], saved[1])
            except Exception:
                logging.warning("Telegram operation failed", exc_info=True)
            clear_status_message(user_id)
    sent = await callback.message.answer(text, parse_mode="HTML", reply_markup=markup)
    set_status_message(user_id, sent.chat.id, sent.message_id)


async def delete_user_message(message: Message):
    try:
        await message.delete()
    except Exception:
        logging.warning("Telegram operation failed", exc_info=True)


async def replace_interface_with_document(message_or_callback, path, caption: str):
    user_id = message_or_callback.from_user.id
    bot = message_or_callback.bot
    source_message = message_or_callback.message if isinstance(message_or_callback, CallbackQuery) else message_or_callback
    saved = get_status_message(user_id)
    if saved:
        try:
            await bot.delete_message(saved[0], saved[1])
        except Exception:
            logging.warning("Telegram operation failed", exc_info=True)
        clear_status_message(user_id)
    sent = await bot.send_document(
        chat_id=source_message.chat.id,
        document=FSInputFile(path),
        caption=caption,
        reply_markup=main_menu(),
    )
    set_status_message(user_id, sent.chat.id, sent.message_id)
