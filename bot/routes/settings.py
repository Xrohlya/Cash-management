from bot.interface import send_transient, edit_interface, delete_user_message
from html import escape
from aiogram import F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from database.repository import list_recurring_payments, list_income_sources
from services.budget import money
from aiogram import Router
from bot.routes.common import answer_callback

router = Router(name="settings")


def recurring_payments_text(user_id: int) -> str:
    payments = list_recurring_payments(user_id)
    lines = ["🔁 <b>РЕГУЛЯРНЫЕ ПЛАТЕЖИ</b>", ""]
    if not payments:
        lines.append("Платежей пока нет. Добавьте их в Mini App → Настройки.")
        return "\n".join(lines)
    for payment in payments:
        kind = "Квартира" if payment["kind"] == "rent" else "Расход"
        lines.append(
            f"• {escape(payment['title'])} — <b>{money(payment['amount'])} ₽</b> "
            f"({payment['day_of_month']}-го, {kind})"
        )
    lines.extend(["", "Новый платёж начинает действовать со следующей назначенной даты."])
    return "\n".join(lines)


@router.callback_query(F.data == "recurring")
async def cb_recurring(callback: CallbackQuery):
    await edit_interface(callback, recurring_payments_text(callback.from_user.id))
    await answer_callback(callback)


def income_sources_text(user_id: int) -> str:
    sources = list_income_sources(user_id)
    lines = ["💼 <b>ИСТОЧНИКИ ДОХОДА</b>", ""]
    active = [source for source in sources if int(source["active"])]
    if not active:
        lines.append("Источников пока нет. Создайте их в Mini App → Настройки.")
    for source in active:
        lines.extend([
            f"• <b>{escape(source['name'])}</b> · удержание {float(source['withholding_percent']):g}%",
            f"  Доход: {money(source['gross_total'])} ₽ · удержано: {money(source['withheld_total'])} ₽",
            f"  <code>получил 30000 {escape(source['name'].casefold())}</code>",
        ])
    lines.extend(["", "Без названия источника доход полностью поступает на основной счёт."])
    return "\n".join(lines)


@router.callback_query(F.data == "income_sources")
async def cb_income_sources(callback: CallbackQuery):
    await edit_interface(callback, income_sources_text(callback.from_user.id))
    await answer_callback(callback)


@router.message(Command("sources"))
async def cmd_income_sources(message: Message):
    await delete_user_message(message)
    await send_transient(message, income_sources_text(message.from_user.id))


@router.message(Command("recurring"))
async def cmd_recurring(message: Message):
    await delete_user_message(message)
    await send_transient(message, recurring_payments_text(message.from_user.id))
