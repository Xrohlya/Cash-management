from datetime import date, timedelta
from database.repository import (
    get_month,
    financial_period_end,
    get_status_snapshot,
)


def days_left_in_month(user_id: int):
    today = date.today()
    return max(0, (financial_period_end(user_id, today) - today).days)


def available_budget(user_id: int) -> float:
    month = get_month(user_id)
    return float(month["budget"]) - float(month["spent"]) - float(month["rent"]) - float(month["saved"])


def daily_limit(user_id: int):
    remaining = available_budget(user_id)
    days = days_left_in_month(user_id)
    return remaining / days if days else remaining


def money(value: float) -> str:
    return f"{value:,.0f}".replace(",", " ")


def status_from_snapshot(snapshot: dict) -> str:
    savings = snapshot["savings"]
    percent = snapshot["mandatory_percent"]
    budget = snapshot["budget"]
    spent = snapshot["spent"]
    rent = snapshot["rent"]
    saved = snapshot["saved"]
    remaining = snapshot["remaining"]
    days = snapshot["days_left"]
    daily = snapshot["daily_limit"]
    spent_today = snapshot["spent_today"]
    left_today = daily - spent_today
    start = snapshot["start"]
    end = snapshot["end"]
    goal = snapshot["goal"]
    goal_line = ""
    if goal:
        target = float(goal["target"])
        target_date = date.fromisoformat(goal["target_date"])
        need = max(0, target - savings)
        days_to_goal = max(1, (target_date - date.today()).days)
        goal_line = f"\n🎯 Цель: {money(target)} ₽ к {target_date:%d.%m.%Y}\n   Осталось накопить: {money(need)} ₽ · {money(need/days_to_goal)} ₽/день"
    forecast = max(0, snapshot["forecast"])
    return (
        "💰 <b>МОЙ БЮДЖЕТ</b>\n\n"
        f"📅 Финансовый месяц: <b>{start:%d.%m.%Y} — {(end - timedelta(days=1)):%d.%m.%Y}</b>\n"
        f"💳 Доступно: <b>{money(remaining)} ₽</b>\n"
        f"📅 Дней осталось: <b>{days}</b>\n"
        f"💸 Потрачено сегодня: <b>{money(spent_today)} ₽</b>\n"
        f"🎯 Лимит сегодня: <b>{money(daily)} ₽</b>\n"
        f"🟢 Осталось сегодня: <b>{money(left_today)} ₽</b>\n\n"
        f"💰 Бюджет месяца: {money(budget)} ₽\n"
        f"💸 Потрачено: {money(spent)} ₽\n"
        f"🏠 Квартира: {money(rent)} ₽ <i>(отдельно)</i>\n"
        f"🔒 Отложено: {money(saved)} ₽ <i>(накопления)</i>\n"
        f"📉 Обязательный вычет: {percent:g}%\n"
        f"🏦 Накопления всего: {money(savings)} ₽\n"
        f"📈 Прогноз остатка к 19-му: <b>{money(forecast)} ₽</b>"
        f"{goal_line}"
    )


def status(user_id: int, snapshot: dict | None = None) -> str:
    return status_from_snapshot(snapshot or get_status_snapshot(user_id))
