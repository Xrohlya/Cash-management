import logging
from bot.interface import send_transient, update_status, edit_interface, delete_user_message
from aiogram import F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from datetime import datetime
from bot.texts import HELP
from database.repository import ensure_user, get_savings, get_status_message, daily_expense_transactions, average_daily_expense
from services.budget import money
from aiogram import Router
from bot.routes.common import answer_callback, transient_messages

router = Router(name="budget")


@router.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    ensure_user(user_id, message.from_user.first_name or "", message.from_user.username or "")
    await delete_user_message(message)
    await update_status(message, user_id)


@router.message(Command("help"))
async def cmd_help(message: Message):
    await delete_user_message(message)
    sent = await send_transient(message, HELP, parse_mode="HTML")


@router.message(Command("status"))
async def cmd_status(message: Message):
    user_id = message.from_user.id
    ensure_user(user_id)
    await delete_user_message(message)
    await update_status(message, user_id)


@router.message(Command("clear"))
async def cmd_clear(message: Message):
    user_id = message.from_user.id
    status_ref = get_status_message(user_id)
    chat_id = message.chat.id
    ids = set(transient_messages.get(chat_id, set()))
    ids.add(message.message_id)
    if status_ref and status_ref[0] == chat_id:
        ids.discard(status_ref[1])

    for message_id in ids:
        try:
            await message.bot.delete_message(chat_id, message_id)
        except Exception:
            logging.warning("Telegram operation failed", exc_info=True)
    transient_messages.pop(chat_id, None)
    await update_status(message, user_id)


@router.message(Command("savings"))
async def cmd_savings(message: Message):
    value = get_savings(message.from_user.id)
    await delete_user_message(message)
    await update_status(message, message.from_user.id)


@router.message(Command("setpercent"))
async def cmd_setpercent(message: Message):
    await delete_user_message(message)
    await send_transient(message, "Проценты источников дохода меняются только в Mini App → Настройки.")


@router.callback_query(F.data == "clear_chat")
async def cb_clear_chat(callback: CallbackQuery):
    user_id = callback.from_user.id
    chat_id = callback.message.chat.id
    status_ref = get_status_message(user_id)
    ids = set(transient_messages.get(chat_id, set()))
    if status_ref and status_ref[0] == chat_id:
        ids.discard(status_ref[1])

    for message_id in ids:
        try:
            await callback.bot.delete_message(chat_id, message_id)
        except Exception:
            logging.warning("Telegram operation failed", exc_info=True)
    transient_messages.pop(chat_id, None)
    await update_status(callback, user_id)
    await answer_callback(callback, "Чат очищен")


@router.callback_query(F.data == "today")
async def cb_today(callback: CallbackQuery):
    user_id = callback.from_user.id
    rows = daily_expense_transactions(user_id)
    total = sum(float(row["amount"]) for row in rows)
    average = average_daily_expense(user_id)

    lines = ["📆 <b>СЕГОДНЯ</b>", ""]
    if rows:
        for row in rows:
            created = row["created_at"]
            try:
                time = datetime.fromisoformat(created).strftime("%H:%M")
            except (ValueError, TypeError):
                time = ""
            time_part = f"{time}  " if time else ""
            lines.append(f"{time_part}• {row['description']} — <b>{money(row['amount'])} ₽</b>")
    else:
        lines.append("Сегодня расходов пока нет.")

    lines.extend([
        "",
        f"💸 <b>Итого сегодня: {money(total)} ₽</b>",
        f"📊 Средний расход в день: <b>{money(average)} ₽</b>",
        "<i>Среднее считается с начала текущего финансового месяца (20-го числа) по сегодня.</i>",
    ])

    try:
        await edit_interface(callback, "\n".join(lines))
    except Exception:
        logging.warning("Telegram operation failed", exc_info=True)
    await answer_callback(callback)


@router.callback_query(F.data == "status")
async def cb_status(callback: CallbackQuery):
    await update_status(callback, callback.from_user.id)
    await answer_callback(callback)


@router.callback_query(F.data == "savings")
async def cb_savings(callback: CallbackQuery):
    await update_status(callback, callback.from_user.id)
    await answer_callback(callback)


@router.callback_query(F.data == "help")
async def cb_help(callback: CallbackQuery):
    try:
        await edit_interface(callback, HELP)
    except Exception:
        logging.warning("Telegram operation failed", exc_info=True)
    await answer_callback(callback)
