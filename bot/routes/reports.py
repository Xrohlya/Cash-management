import logging
from html import escape
from bot.keyboards import history_menu
from bot.interface import send_transient, edit_interface, delete_user_message, replace_interface_with_document
from aiogram import F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from datetime import timedelta
from database.repository import recent_transactions
from services.budget import money
from services.wallet_history import history_line
from services.report import build_monthly_report, parse_report_period
from aiogram import Router
from bot.routes.common import answer_callback

router = Router(name="reports")


@router.message(Command("excel"))
async def cmd_excel(message: Message):
    from services.excel_report import build_excel_report
    user_id = message.from_user.id
    raw = message.text.removeprefix("/excel").strip()
    try:
        start, end = parse_report_period(user_id, raw or None)
    except ValueError:
        await delete_user_message(message); await send_transient(message, "Пример: <code>/excel 2026-09</code>", parse_mode="HTML"); return
    await delete_user_message(message)
    try:
        path = build_excel_report(user_id, start, end)
        await replace_interface_with_document(message, path, f"📊 Excel: {start:%d.%m.%Y} — {(end-timedelta(days=1)):%d.%m.%Y}")
    except Exception as exc:
        await send_transient(message, f"⚠️ Ошибка Excel: <code>{str(exc)[:300].replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')}</code>", parse_mode="HTML")


@router.message(Command("report"))
async def cmd_report(message: Message):
    user_id = message.from_user.id
    raw = message.text.removeprefix("/report").strip()
    try:
        start, end = parse_report_period(user_id, raw or None)
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
        await replace_interface_with_document(
            message, report_path,
            f"📊 Отчёт за {start:%d.%m.%Y} — {(end - timedelta(days=1)):%d.%m.%Y}",
        )
    except Exception as exc:
        await send_transient(message, f"⚠️ Не удалось создать отчёт: <code>{str(exc)[:300]}</code>", parse_mode="HTML")


@router.message(Command("history"))
async def cmd_history(message: Message):
    await delete_user_message(message)
    await send_transient(message, history_text(message.from_user.id), parse_mode="HTML", reply_markup=history_menu())


def history_text(user_id: int) -> str:
    rows = recent_transactions(user_id)
    if not rows:
        return "📋 История пока пустая."
    labels = {"income": "+ ДОХОД", "mandatory": "− 6%", "expense": "− РАСХОД", "recurring": "🔁 РЕГУЛЯРНЫЙ", "rent": "🏠 КВАРТИРА", "save": "🔒 НАКОПЛЕНИЯ"}
    lines = ["📋 <b>Последние операции</b>\n"]
    for row in rows:
        lines.append(history_line(row, labels))
    return "\n".join(lines)


@router.callback_query(F.data == "report")
async def cb_report(callback: CallbackQuery):
    await export_report(callback, "pdf")


@router.callback_query(F.data == "excel")
async def cb_excel(callback: CallbackQuery):
    await export_report(callback, "excel")


async def export_report(callback: CallbackQuery, file_format: str):
    user_id = callback.from_user.id
    title = "Excel" if file_format == "excel" else "PDF"
    await answer_callback(callback, f"Готовлю {title}…")
    try:
        start, end = parse_report_period(user_id)
        if file_format == "excel":
            from services.excel_report import build_excel_report
            report_path = build_excel_report(user_id, start, end)
        else:
            report_path = build_monthly_report(user_id, start, end)
        await replace_interface_with_document(
            callback, report_path,
            f"📊 {title}: {start:%d.%m.%Y} — {(end - timedelta(days=1)):%d.%m.%Y}",
        )
    except Exception as exc:
        # Не создаём ещё одно сообщение: показываем ошибку в единственном
        # постоянном сообщении интерфейса и даём возможность вернуться к меню.
        try:
            await edit_interface(
                callback,
                f"⚠️ <b>Не удалось создать отчёт</b>\n\n<code>{escape(str(exc)[:300])}</code>",
                reply_markup=history_menu(),
            )
        except Exception:
            logging.warning("Telegram operation failed", exc_info=True)


@router.callback_query(F.data == "history")
async def cb_history(callback: CallbackQuery):
    try:
        await edit_interface(callback, history_text(callback.from_user.id), reply_markup=history_menu())
    except Exception:
        logging.warning("Telegram operation failed", exc_info=True)
    await answer_callback(callback)
