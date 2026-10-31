"""Explicit confirmation of an unrecognised income source."""
import time
from uuid import uuid4

from aiogram import F, Router
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from bot.interface import delete_user_message, edit_interface, send_transient, update_status
from bot.routes.common import pending, set_pending, clear_pending
from database.repository import add_income, add_income_from_source, list_income_sources
from services.formatting import money
from services.text_matching import income_suggestions

router = Router(name="income_matching")


async def suggest_income(message, amount, sources):
    candidates = income_suggestions(message.text, sources) or sources[:3]
    token = uuid4().hex[:12]
    set_pending(message.from_user.id, "matched_income", amount=amount, token=token,
                expires=time.monotonic() + 300,
                sources={int(row["id"]): (row["name"], float(row["withholding_percent"]))
                         for row in candidates})
    buttons = [[InlineKeyboardButton(
        text=f"{row['name']} · {float(row['withholding_percent']):g}%",
        callback_data=f"match_income:{token}:{row['id']}",
    )] for row in candidates]
    buttons.extend([
        [InlineKeyboardButton(text="Без источника · 0%", callback_data=f"match_income:{token}:0")],
        [InlineKeyboardButton(text="Отмена", callback_data="cancel")],
    ])
    await delete_user_message(message)
    await send_transient(message,
        f"<b>Уточни источник дохода</b>\nСумма: <b>{money(amount)} ₽</b>\n"
        "Пока ничего не зачислено. Выбери источник и процент удержания.",
        parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("match_income:"))
async def confirm_matched_income(callback):
    parts = callback.data.split(":")
    user_id = callback.from_user.id
    item = pending.get(user_id)
    if len(parts) != 3 or not parts[2].isdigit() or not item or item["kind"] != "matched_income" or item["token"] != parts[1]:
        return
    if time.monotonic() > item["expires"]:
        clear_pending(user_id)
        await edit_interface(callback, "Подтверждение устарело. Отправь доход ещё раз.")
        return
    source_id = int(parts[2])
    if source_id:
        current = next((row for row in list_income_sources(user_id)
                        if int(row["id"]) == source_id and int(row["active"])), None)
        if not current or item["sources"].get(source_id) != (current["name"], float(current["withholding_percent"])):
            clear_pending(user_id)
            await edit_interface(callback, "Источник изменился. Отправь доход ещё раз.")
            return
        try:
            add_income_from_source(user_id, item["amount"], source_id, current["name"],
                                   request_id=f"income-match:{user_id}:{item['token']}",
                                   expected_source=item["sources"][source_id])
        except ValueError:
            clear_pending(user_id)
            await edit_interface(callback, "Источник изменился. Отправь доход ещё раз.")
            return
    else:
        add_income(user_id, item["amount"], 0, request_id=f"income-match:{user_id}:{item['token']}")
    clear_pending(user_id)
    await update_status(callback, user_id)
