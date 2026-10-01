from bot.interface import send_transient, update_status, edit_interface, delete_user_message
from aiogram import F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from bot.keyboards import confirm_keyboard
from database.repository import ensure_user, add_income, add_expense, add_rent, add_to_savings, add_bulk_expenses, find_income_source, add_income_from_source
from services.budget import money, available_budget
from services.parser import parse_amount, parse_expense
from aiogram import Router
from bot.routes.common import answer_callback, clear_pending, parse_expense_list, set_pending

router = Router(name="operations")


@router.message(Command("income"))
async def cmd_income(message: Message):
    amount = parse_amount(message.text)
    if amount is None or amount <= 0:
        await delete_user_message(message)
        await send_transient(message, "Пример: <code>/income 200000</code>", parse_mode="HTML")
        return

    user_id = message.from_user.id
    ensure_user(user_id)
    source = find_income_source(user_id, message.text)
    if source:
        add_income_from_source(user_id, amount, source["id"], source["name"])
    else:
        add_income(user_id, amount, 0)
    await delete_user_message(message)
    await update_status(message, user_id)


@router.message(Command("expense"))
async def cmd_expense(message: Message):
    user_id = message.from_user.id
    text = message.text.removeprefix("/expense").strip()
    ensure_user(user_id)

    if "\n" in text:
        items = parse_expense_list(text)
        if items:
            total = round(sum(amount for amount, _ in items), 2)
            available = available_budget(user_id)
            if total > available:
                await delete_user_message(message)
                await send_transient(message, f"⚠️ Сумма расходов {money(total)} ₽ больше доступного бюджета ({money(available)} ₽).", parse_mode="HTML")
                return
            set_pending(user_id, "bulk_expense", items=items)
            lines = ["🧾 <b>Проверь расходы</b>\n"]
            for amount, description in items:
                lines.append(f"• {description} — {money(amount)} ₽")
            lines.append(f"\n<b>Итого: {money(total)} ₽</b>\n\nСохранить все расходы?")
            await delete_user_message(message)
            sent = await send_transient(message, "\n".join(lines), parse_mode="HTML", reply_markup=confirm_keyboard("confirm_bulk_expense"))
            return

    amount, description = parse_expense(text)
    if amount is None or amount <= 0:
        await delete_user_message(message)
        await send_transient(message, "Пример: <code>/expense 2500 магазин</code>", parse_mode="HTML")
        return

    available = available_budget(user_id)
    if amount > available:
        await delete_user_message(message)
        await send_transient(message, f"⚠️ Расход {money(amount)} ₽ больше доступного бюджета ({money(available)} ₽).", parse_mode="HTML")
        return

    add_expense(user_id, amount, description)
    await delete_user_message(message)
    await update_status(message, user_id)


@router.message(Command("expenses"))
async def cmd_expenses(message: Message):
    user_id = message.from_user.id
    text = message.text.removeprefix("/expenses").strip()
    items = parse_expense_list(text)
    if not items:
        await delete_user_message(message)
        await send_transient(message, "Пример:\n<code>/expenses\nпродукты 3500\nбензин 2500\nкафе 800</code>", parse_mode="HTML")
        return

    ensure_user(user_id)
    total = round(sum(amount for amount, _ in items), 2)
    available = available_budget(user_id)
    if total > available:
        await delete_user_message(message)
        await send_transient(message, f"⚠️ Сумма расходов {money(total)} ₽ больше доступного бюджета ({money(available)} ₽).", parse_mode="HTML")
        return

    set_pending(user_id, "bulk_expense", items=items)
    lines = ["🧾 <b>Проверь расходы</b>\n"]
    for amount, description in items:
        lines.append(f"• {description} — {money(amount)} ₽")
    lines.append(f"\n<b>Итого: {money(total)} ₽</b>\n\nСохранить все расходы?")
    await delete_user_message(message)
    await send_transient(message, "\n".join(lines), parse_mode="HTML", reply_markup=confirm_keyboard("confirm_bulk_expense"))


@router.message(Command("rent"))
async def cmd_rent(message: Message):
    amount = parse_amount(message.text)
    if amount is None or amount <= 0:
        await delete_user_message(message)
        await send_transient(message, "Пример: <code>/rent 40000</code>", parse_mode="HTML")
        return
    user_id = message.from_user.id
    ensure_user(user_id)
    available = available_budget(user_id)
    if amount > available:
        await delete_user_message(message)
        await send_transient(message, f"⚠️ Нельзя учесть квартиру {money(amount)} ₽: доступно только {money(available)} ₽.", parse_mode="HTML")
        return
    set_pending(user_id, "rent", amount)
    await delete_user_message(message)
    await send_transient(
        message,
        f"🏠 <b>Квартира</b>\n\nСумма: <b>{money(amount)} ₽</b>\nЭта сумма учитывается отдельно и не попадает в «Потрачено».\n\nПодтвердить?",
        parse_mode="HTML", reply_markup=confirm_keyboard("confirm_rent")
    )


@router.message(Command("save"))
async def cmd_save(message: Message):
    amount = parse_amount(message.text)
    if amount is None or amount <= 0:
        await delete_user_message(message)
        await send_transient(message, "Пример: <code>/save 30000</code>", parse_mode="HTML")
        return
    user_id = message.from_user.id
    ensure_user(user_id)
    available = available_budget(user_id)
    if amount > available:
        await delete_user_message(message)
        await send_transient(message, f"⚠️ Нельзя отложить {money(amount)} ₽: доступно только {money(available)} ₽.", parse_mode="HTML")
        return
    set_pending(user_id, "save", amount)
    await delete_user_message(message)
    await send_transient(
        message,
        f"🔒 <b>Отложить в накопления</b>\n\nСумма: <b>{money(amount)} ₽</b>\nПосле подтверждения бюджет уменьшится, а накопления увеличатся.\n\nПодтвердить?",
        parse_mode="HTML", reply_markup=confirm_keyboard("confirm_save")
    )


@router.message(Command("cancel"))
async def cmd_cancel(message: Message):
    clear_pending(message.from_user.id)
    await delete_user_message(message)
    await update_status(message, message.from_user.id)


@router.callback_query(F.data == "confirm_rent")
async def cb_confirm_rent(callback: CallbackQuery):
    user_id = callback.from_user.id
    operation = clear_pending(user_id)
    if not operation or operation["kind"] != "rent":
        await answer_callback(callback, "Операция уже отменена или выполнена.", show_alert=True)
        return
    amount = operation["amount"]
    if amount > available_budget(user_id):
        await edit_interface(callback, "⚠️ К моменту подтверждения доступного бюджета уже недостаточно.")
        await answer_callback(callback)
        return
    if not add_rent(user_id, amount):
        await edit_interface(callback, "⚠️ К моменту подтверждения доступного бюджета уже недостаточно.")
        await answer_callback(callback)
        return
    await update_status(callback, user_id)
    await answer_callback(callback, "Квартира учтена")


@router.callback_query(F.data == "confirm_save")
async def cb_confirm_save(callback: CallbackQuery):
    user_id = callback.from_user.id
    operation = clear_pending(user_id)
    if not operation or operation["kind"] != "save":
        await answer_callback(callback, "Операция уже отменена или выполнена.", show_alert=True)
        return
    amount = operation["amount"]
    if amount > available_budget(user_id):
        await edit_interface(callback, "⚠️ К моменту подтверждения доступного бюджета уже недостаточно.")
        await answer_callback(callback)
        return
    if not add_to_savings(user_id, amount):
        await edit_interface(callback, "⚠️ К моменту подтверждения доступного бюджета уже недостаточно.")
        await answer_callback(callback)
        return
    await update_status(callback, user_id)
    await answer_callback(callback, "Сбережения обновлены")


@router.callback_query(F.data == "confirm_bulk_expense")
async def cb_confirm_bulk_expense(callback: CallbackQuery):
    user_id = callback.from_user.id
    operation = clear_pending(user_id)
    if not operation or operation["kind"] != "bulk_expense":
        await answer_callback(callback, "Операция уже отменена или выполнена.", show_alert=True)
        return
    items = operation["items"]
    total = round(sum(amount for amount, _ in items), 2)
    available = available_budget(user_id)
    if total > available:
        await edit_interface(callback, f"⚠️ К моменту подтверждения доступно только {money(available)} ₽, а нужно {money(total)} ₽.")
        await answer_callback(callback)
        return
    if not add_bulk_expenses(user_id, items):
        await edit_interface(callback, "⚠️ К моменту подтверждения доступного бюджета уже недостаточно.")
        await answer_callback(callback)
        return
    await update_status(callback, user_id)
    await answer_callback(callback, f"Записано {len(items)} расходов")


@router.callback_query(F.data == "cancel")
async def cb_cancel(callback: CallbackQuery):
    clear_pending(callback.from_user.id)
    await update_status(callback, callback.from_user.id)
    await answer_callback(callback, "Операция отменена")
