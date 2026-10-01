from bot.interface import send_transient, update_status, edit_interface, delete_user_message
from aiogram import F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from datetime import date
from services.budget import money
from services.parser import parse_amount, extract_date
from services.analytics import current_period_stats, comparison, set_goal, get_goal, clear_goal
from aiogram import Router
from bot.routes.common import answer_callback

router = Router(name="analytics")


@router.callback_query(F.data == "analytics")
async def cb_analytics(callback: CallbackQuery):
    stats = current_period_stats(callback.from_user.id)
    cats = sorted(stats["categories"].items(), key=lambda x: x[1], reverse=True)
    lines = ["📊 <b>АНАЛИТИКА</b>", "", f"Расходы: <b>{money(stats['expenses'])} ₽</b>", f"Среднее в день: <b>{money(stats['avg'])} ₽</b>", ""]
    if cats:
        for name, value in cats[:10]:
            pct = value / stats["expenses"] * 100 if stats["expenses"] else 0
            lines.append(f"• {name}: {money(value)} ₽ ({pct:.0f}%)")
    else:
        lines.append("Расходов пока нет.")
    await edit_interface(callback, "\n".join(lines))
    await answer_callback(callback)


@router.callback_query(F.data == "forecast")
async def cb_forecast(callback: CallbackQuery):
    stats = current_period_stats(callback.from_user.id)
    remaining_days = max(0, (stats["end"] - date.today()).days)
    text = ("📈 <b>ПРОГНОЗ</b>\n\n"
            f"Текущие расходы: <b>{money(stats['expenses'])} ₽</b>\n"
            f"Среднее: <b>{money(stats['avg'])} ₽/день</b>\n"
            f"Дней осталось: <b>{remaining_days}</b>\n\n"
            f"Доступно сейчас: <b>{money(stats['remaining'])} ₽</b>\n"
            f"Прогноз остатка к 19-му: <b>{money(max(0, stats['forecast']))} ₽</b>")
    await edit_interface(callback, text)
    await answer_callback(callback)


@router.callback_query(F.data == "compare")
async def cb_compare(callback: CallbackQuery):
    current, previous = comparison(callback.from_user.id)
    delta = current - previous
    text = ("📊 <b>СРАВНЕНИЕ МЕСЯЦЕВ</b>\n\n"
            f"Текущий период: <b>{money(current)} ₽</b>\n"
            f"Предыдущий: <b>{money(previous)} ₽</b>\n"
            f"Разница: <b>{'+' if delta >= 0 else ''}{money(delta)} ₽</b>")
    await edit_interface(callback, text)
    await answer_callback(callback)


@router.callback_query(F.data == "goal")
async def cb_goal(callback: CallbackQuery):
    goal = get_goal(callback.from_user.id)
    if not goal:
        text = "🎯 <b>Цель накопления</b>\n\nУстановить: <code>/goal 300000 01.06.2027</code>\nУдалить: <code>/goal off</code>"
    else:
        target, target_date = goal
        text = f"🎯 <b>ЦЕЛЬ</b>\n\n{money(target)} ₽ к {target_date:%d.%m.%Y}\n\nИзменить: <code>/goal 300000 01.06.2027</code>"
    await edit_interface(callback, text)
    await answer_callback(callback)


@router.message(Command("goal"))
async def cmd_goal(message: Message):
    user_id = message.from_user.id
    raw = message.text.removeprefix("/goal").strip()
    if raw.casefold() in ("off", "нет", "удалить"):
        clear_goal(user_id)
        await delete_user_message(message); await update_status(message, user_id); return
    parts = raw.split()
    target = parse_amount(raw)
    target_date = None
    if len(parts) >= 2:
        target_date = extract_date(parts[1])
    if target is None or target <= 0 or target_date is None or target_date <= date.today():
        await delete_user_message(message)
        await send_transient(message, "Пример: <code>/goal 300000 01.06.2027</code>", parse_mode="HTML")
        return
    set_goal(user_id, target, target_date)
    await delete_user_message(message); await update_status(message, user_id)
