from html import escape

from aiogram import F, Router
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.interface import delete_user_message, send_transient, update_status, edit_interface
from bot.routes.common import set_pending, clear_pending, answer_callback
from database.accounts import list_extra_accounts
from database.wallets import spend, transfer, refund, refundable_expenses
from services.categories import normalize_expense_category
from services.wallet_commands import parse_wallet_command

router = Router(name="wallets")


@router.message(F.text.regexp(r"(?i)^/?(?:возврат|refund|перевод|transfer)\b|^/?(?:расход|expense)\s+\d+(?:[.,]\d+)?\s+(?:из|со?\s+сч[её]та)\b"))
async def wallet_message(message):
    user_id = message.from_user.id
    request_id = f"telegram-wallet-{message.chat.id}-{message.message_id}"
    try:
        command, amount, data = parse_wallet_command(message.text, list_extra_accounts(user_id))
        if command == "transfer":
            transfer(user_id, *data, amount, request_id)
        elif command == "expense":
            spend(user_id, data[0], amount, data[1], request_id)
        else:
            candidates = [row for row in refundable_expenses(user_id) if float(row["refundable"]) >= amount and (str(row["id"]) == data.lstrip("#") or normalize_expense_category(data).casefold() == row["description"].casefold())]
            if not candidates:
                raise ValueError("Не найден расход с достаточной суммой для возврата")
            if len(candidates) > 1:
                set_pending(user_id, "refund", amount, request_id=request_id, ids=[row["id"] for row in candidates[:20]])
                buttons = [[InlineKeyboardButton(text=f"#{row['id']} · {row['description']} · {row['created_at'][:10]} · {row['refundable']:g} ₽", callback_data=f"wallet_refund:{row['id']}")] for row in candidates[:20]]
                buttons.append([InlineKeyboardButton(text="Отмена", callback_data="cancel")])
                await send_transient(message, "Выберите покупку для возврата:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
                await delete_user_message(message)
                return
            refund(user_id, candidates[0]["id"], amount, request_id)
        await update_status(message, user_id)
        await delete_user_message(message)
    except ValueError as exc:
        await send_transient(message, escape(str(exc)))


@router.callback_query(F.data.startswith("wallet_refund:"))
async def choose_refund(callback):
    operation = clear_pending(callback.from_user.id)
    original_id = int(callback.data.split(":")[1])
    if not operation or operation["kind"] != "refund" or original_id not in operation["ids"]:
        await answer_callback(callback, "Выбор устарел. Введите возврат заново.", show_alert=True)
        return
    try:
        refund(callback.from_user.id, original_id, operation["amount"], operation["request_id"])
        await update_status(callback, callback.from_user.id)
    except ValueError as exc:
        await edit_interface(callback, escape(str(exc)))
