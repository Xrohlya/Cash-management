from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, FSInputFile
from datetime import datetime, timedelta, date

from bot.keyboards import main_menu, confirm_keyboard
from bot.texts import WELCOME, HELP
from database.repository import (
    ensure_user, get_percent, set_percent, get_savings,
    add_income, add_expense, add_rent, add_to_savings,
    add_bulk_expenses,
    recent_transactions, get_status_message, set_status_message,
    clear_status_message, daily_expense_transactions, average_daily_expense,
)
from services.budget import status, money, available_budget
from services.parser import parse_amount, parse_expense, looks_like_income, extract_date, strip_date_words
from services.report import build_monthly_report, parse_report_period
from services.analytics import current_period_stats, comparison, set_goal, get_goal, clear_goal

router = Router()
router.message.filter(F.chat.type == "private")
router.callback_query.filter(F.message.chat.type == "private")
pending = {}

# Сообщения бота, которые можно удалить командой /clear в текущем запуске.
transient_messages = {}


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


async def send_transient(message: Message, text: str, **kwargs):
    """Show temporary-looking text by editing the ONE persistent bot message."""
    user_id = message.from_user.id
    ensure_user(user_id)
    saved = get_status_message(user_id)
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
        except Exception:
            clear_status_message(user_id)

    sent = await message.answer(text, parse_mode=parse_mode, reply_markup=reply_markup)
    set_status_message(user_id, sent.chat.id, sent.message_id)
    return sent


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


async def update_status(message_or_callback, user_id: int):
    """Keep one persistent status message per user and update it in place."""
    ensure_user(user_id)
    text = status(user_id)
    markup = main_menu()
    saved = get_status_message(user_id)

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
            return
        except Exception:
            # Сообщение могли удалить вручную или Telegram больше не даёт его редактировать.
            clear_status_message(user_id)

    if isinstance(message_or_callback, CallbackQuery):
        sent = await message_or_callback.message.answer(text, parse_mode="HTML", reply_markup=markup)
    else:
        sent = await message_or_callback.answer(text, parse_mode="HTML", reply_markup=markup)
    set_status_message(user_id, sent.chat.id, sent.message_id)


async def delete_user_message(message: Message):
    try:
        await message.delete()
    except Exception:
        pass


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
            pass
    transient_messages.pop(chat_id, None)
    await update_status(message, user_id)


@router.message(Command("savings"))
async def cmd_savings(message: Message):
    value = get_savings(message.from_user.id)
    await delete_user_message(message)
    await update_status(message, message.from_user.id)


@router.message(Command("setpercent"))
async def cmd_setpercent(message: Message):
    amount = parse_amount(message.text)
    if amount is None or not 0 <= amount <= 100:
        await delete_user_message(message)
        await send_transient(message, "Пример: <code>/setpercent 6</code>", parse_mode="HTML")
        return
    set_percent(message.from_user.id, amount)
    await delete_user_message(message)
    await update_status(message, message.from_user.id)


@router.message(Command("income"))
async def cmd_income(message: Message):
    amount = parse_amount(message.text)
    if amount is None or amount <= 0:
        await delete_user_message(message)
        await send_transient(message, "Пример: <code>/income 200000</code>", parse_mode="HTML")
        return

    user_id = message.from_user.id
    ensure_user(user_id)
    percent = get_percent(user_id)
    add_income(user_id, amount, percent)
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


@router.message(Command("excel"))
async def cmd_excel(message: Message):
    from services.excel_report import build_excel_report
    user_id = message.from_user.id
    raw = message.text.removeprefix("/excel").strip()
    try:
        start, end = parse_report_period(raw or None)
    except ValueError:
        await delete_user_message(message); await send_transient(message, "Пример: <code>/excel 2026-09</code>", parse_mode="HTML"); return
    await delete_user_message(message)
    try:
        path = build_excel_report(user_id, start, end)
        await message.bot.send_document(chat_id=message.chat.id, document=FSInputFile(path), caption=f"📊 Excel: {start:%d.%m.%Y} — {(end-timedelta(days=1)):%d.%m.%Y}")
    except Exception as exc:
        await send_transient(message, f"⚠️ Ошибка Excel: <code>{str(exc)[:300].replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')}</code>", parse_mode="HTML")


@router.message(Command("report"))
async def cmd_report(message: Message):
    user_id = message.from_user.id
    raw = message.text.removeprefix("/report").strip()
    try:
        start, end = parse_report_period(raw or None)
    except ValueError:
        await delete_user_message(message)
        await send_transient(
            message,
            "Пример: <code>/report</code> — текущий месяц\n"
            "или <code>/report 2026-09</code> — период 20.09–19.10.2026.",
            parse_mode="HTML",
        )
        return

    await delete_user_message(message)
    try:
        report_path = build_monthly_report(user_id, start, end)
        await message.bot.send_document(
            chat_id=message.chat.id,
            document=FSInputFile(report_path),
            caption=f"📊 Отчёт за {start:%d.%m.%Y} — {(end - timedelta(days=1)):%d.%m.%Y}",
        )
    except Exception as exc:
        await send_transient(message, f"⚠️ Не удалось создать отчёт: <code>{str(exc)[:300]}</code>", parse_mode="HTML")


@router.message(Command("history"))
async def cmd_history(message: Message):
    rows = recent_transactions(message.from_user.id)
    await delete_user_message(message)
    if not rows:
        await send_transient(message, "История пока пустая.")
        return
    labels = {"income": "+ ДОХОД", "mandatory": "− 6%", "expense": "− РАСХОД", "rent": "🏠 КВАРТИРА", "save": "🔒 НАКОПЛЕНИЯ"}
    lines = ["📋 <b>Последние операции</b>\n"]
    for row in rows:
        lines.append(f"{labels.get(row['kind'], row['kind'])}: {money(row['amount'])} ₽ — {row['description']}")
    await send_transient(message, "\n".join(lines), parse_mode="HTML")


async def finish_callback(callback: CallbackQuery, text=None):
    user_id = callback.from_user.id
    if text is not None:
        try:
            await callback.message.edit_text(text, parse_mode="HTML", reply_markup=main_menu())
        except Exception:
            pass
    await update_status(callback, user_id)
    await callback.answer()


@router.callback_query(F.data == "confirm_rent")
async def cb_confirm_rent(callback: CallbackQuery):
    user_id = callback.from_user.id
    operation = clear_pending(user_id)
    if not operation or operation["kind"] != "rent":
        await callback.answer("Операция уже отменена или выполнена.", show_alert=True)
        return
    amount = operation["amount"]
    if amount > available_budget(user_id):
        await callback.message.edit_text("⚠️ К моменту подтверждения доступного бюджета уже недостаточно.")
        await callback.answer()
        return
    if not add_rent(user_id, amount):
        await callback.message.edit_text("⚠️ К моменту подтверждения доступного бюджета уже недостаточно.")
        await callback.answer()
        return
    await update_status(callback, user_id)
    await callback.answer("Квартира учтена")


@router.callback_query(F.data == "confirm_save")
async def cb_confirm_save(callback: CallbackQuery):
    user_id = callback.from_user.id
    operation = clear_pending(user_id)
    if not operation or operation["kind"] != "save":
        await callback.answer("Операция уже отменена или выполнена.", show_alert=True)
        return
    amount = operation["amount"]
    if amount > available_budget(user_id):
        await callback.message.edit_text("⚠️ К моменту подтверждения доступного бюджета уже недостаточно.")
        await callback.answer()
        return
    if not add_to_savings(user_id, amount):
        await callback.message.edit_text("⚠️ К моменту подтверждения доступного бюджета уже недостаточно.")
        await callback.answer()
        return
    await update_status(callback, user_id)
    await callback.answer("Сбережения обновлены")


@router.callback_query(F.data == "confirm_bulk_expense")
async def cb_confirm_bulk_expense(callback: CallbackQuery):
    user_id = callback.from_user.id
    operation = clear_pending(user_id)
    if not operation or operation["kind"] != "bulk_expense":
        await callback.answer("Операция уже отменена или выполнена.", show_alert=True)
        return
    items = operation["items"]
    total = round(sum(amount for amount, _ in items), 2)
    available = available_budget(user_id)
    if total > available:
        await callback.message.edit_text(f"⚠️ К моменту подтверждения доступно только {money(available)} ₽, а нужно {money(total)} ₽.")
        await callback.answer()
        return
    if not add_bulk_expenses(user_id, items):
        await callback.message.edit_text("⚠️ К моменту подтверждения доступного бюджета уже недостаточно.")
        await callback.answer()
        return
    await update_status(callback, user_id)
    await callback.answer(f"Записано {len(items)} расходов")


@router.callback_query(F.data == "cancel")
async def cb_cancel(callback: CallbackQuery):
    clear_pending(callback.from_user.id)
    await update_status(callback, callback.from_user.id)
    await callback.answer("Операция отменена")


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
            pass
    transient_messages.pop(chat_id, None)
    await update_status(callback, user_id)
    await callback.answer("Чат очищен")


@router.callback_query(F.data == "report")
async def cb_report(callback: CallbackQuery):
    user_id = callback.from_user.id
    await callback.answer("Готовлю PDF…")
    try:
        start, end = parse_report_period(None)
        report_path = build_monthly_report(user_id, start, end)
        await callback.bot.send_document(
            chat_id=callback.message.chat.id,
            document=FSInputFile(report_path),
            caption=f"📊 Отчёт за {start:%d.%m.%Y} — {(end - timedelta(days=1)):%d.%m.%Y}",
        )
    except Exception as exc:
        # Не создаём ещё одно сообщение: показываем ошибку в единственном
        # постоянном сообщении интерфейса и даём возможность вернуться к меню.
        try:
            await callback.message.edit_text(
                f"⚠️ <b>Не удалось создать отчёт</b>\n\n<code>{str(exc)[:300].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')}</code>",
                parse_mode="HTML",
                reply_markup=main_menu(),
            )
        except Exception:
            pass


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
            except Exception:
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
        await callback.message.edit_text("\n".join(lines), parse_mode="HTML", reply_markup=main_menu())
    except Exception:
        pass
    await callback.answer()


@router.callback_query(F.data == "status")
async def cb_status(callback: CallbackQuery):
    await update_status(callback, callback.from_user.id)
    await callback.answer()


@router.callback_query(F.data == "savings")
async def cb_savings(callback: CallbackQuery):
    await update_status(callback, callback.from_user.id)
    await callback.answer()


@router.callback_query(F.data == "help")
async def cb_help(callback: CallbackQuery):
    try:
        await callback.message.edit_text(HELP, parse_mode="HTML", reply_markup=main_menu())
    except Exception:
        pass
    await callback.answer()


@router.callback_query(F.data == "history")
async def cb_history(callback: CallbackQuery):
    rows = recent_transactions(callback.from_user.id)
    if not rows:
        text = "📋 История пока пустая."
    else:
        labels = {"income": "+ ДОХОД", "mandatory": "− 6%", "expense": "− РАСХОД", "rent": "🏠 КВАРТИРА", "save": "🔒 НАКОПЛЕНИЯ"}
        lines = ["📋 <b>Последние операции</b>\n"]
        for row in rows:
            lines.append(f"{labels.get(row['kind'], row['kind'])}: {money(row['amount'])} ₽ — {row['description']}")
        text = "\n".join(lines)
    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=main_menu())
    except Exception:
        pass
    await callback.answer()



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
    await callback.message.edit_text("\n".join(lines), parse_mode="HTML", reply_markup=main_menu())
    await callback.answer()


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
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=main_menu())
    await callback.answer()


@router.callback_query(F.data == "compare")
async def cb_compare(callback: CallbackQuery):
    current, previous = comparison(callback.from_user.id)
    delta = current - previous
    text = ("📊 <b>СРАВНЕНИЕ МЕСЯЦЕВ</b>\n\n"
            f"Текущий период: <b>{money(current)} ₽</b>\n"
            f"Предыдущий: <b>{money(previous)} ₽</b>\n"
            f"Разница: <b>{'+' if delta >= 0 else ''}{money(delta)} ₽</b>")
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=main_menu())
    await callback.answer()


@router.callback_query(F.data == "goal")
async def cb_goal(callback: CallbackQuery):
    goal = get_goal(callback.from_user.id)
    if not goal:
        text = "🎯 <b>Цель накопления</b>\n\nУстановить: <code>/goal 300000 01.06.2027</code>\nУдалить: <code>/goal off</code>"
    else:
        target, target_date = goal
        text = f"🎯 <b>ЦЕЛЬ</b>\n\n{money(target)} ₽ к {target_date:%d.%m.%Y}\n\nИзменить: <code>/goal 300000 01.06.2027</code>"
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=main_menu())
    await callback.answer()


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
            percent = get_percent(user_id)
            add_income(user_id, amount, percent)
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
