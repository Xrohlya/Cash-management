from bot.interface import send_transient, update_status, delete_user_message
from aiogram import F
from aiogram.types import Message
from datetime import datetime
from bot.keyboards import confirm_keyboard
from database.repository import ensure_user, add_income, add_expense, find_income_source, add_income_from_source
from services.budget import money, available_budget
from services.parser import parse_amount, parse_expense, looks_like_income, extract_date, strip_date_words
from aiogram import Router
from bot.routes.common import parse_expense_list, set_pending

router = Router(name="messages")


@router.message(F.text)
async def plain_text(message: Message):
    text = message.text.strip()
    user_id = message.from_user.id
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
            await send_transient(message, "\n".join(lines), parse_mode="HTML", reply_markup=confirm_keyboard("confirm_bulk_expense"))
            return

    if looks_like_income(text):
        amount = parse_amount(text)
        if amount:
            source = find_income_source(user_id, text)
            if source:
                add_income_from_source(user_id, amount, source["id"], source["name"])
            else:
                add_income(user_id, amount, 0)
            await delete_user_message(message)
            await update_status(message, user_id)
            return

    amount, description = parse_expense(text)
    if amount:
        parsed_day = extract_date(text)
        clean_description = strip_date_words(description or "Расход")
        if parsed_day and parsed_day != datetime.now().date():
            available = available_budget(user_id)
            if amount > available:
                await delete_user_message(message)
                await send_transient(message, f"⚠️ Расход {money(amount)} ₽ больше доступного бюджета ({money(available)} ₽).", parse_mode="HTML")
                return
            add_expense(
                user_id,
                amount,
                clean_description,
                created_at=datetime.combine(parsed_day, datetime.min.time()).replace(hour=12),
            )
            await delete_user_message(message)
            await update_status(message, user_id)
            return
        description = clean_description
        available = available_budget(user_id)
        if amount > available:
            await delete_user_message(message)
            await send_transient(message, f"⚠️ Расход {money(amount)} ₽ больше доступного бюджета ({money(available)} ₽).", parse_mode="HTML")
            return
        add_expense(user_id, amount, description)
        await delete_user_message(message)
        await update_status(message, user_id)
        return

    await delete_user_message(message)
    await send_transient(message, "Не понял сообщение.\n\nНапиши, например:\n<code>магазин 2500</code>\n<code>получил 200000</code>", parse_mode="HTML")
