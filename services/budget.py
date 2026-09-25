from datetime import date, timedelta
from database.repository import get_month, get_percent, get_savings, financial_period_end, financial_period_start, daily_expenses
from services.analytics import current_period_stats, get_goal


def days_left_in_month():
    today = date.today()
    return max(0, (financial_period_end(today) - today).days)


def available_budget(user_id: int) -> float:
    month = get_month(user_id)
    return float(month["budget"]) - float(month["spent"]) - float(month["rent"]) - float(month["saved"])


def daily_limit(user_id: int):
    remaining = available_budget(user_id)
    days = days_left_in_month()
    return remaining / days if days else remaining


def money(value: float) -> str:
    return f"{value:,.0f}".replace(",", " ")


def status(user_id: int) -> str:
    month = get_month(user_id)
    savings = get_savings(user_id)
    percent = get_percent(user_id)
    budget = float(month["budget"]); spent = float(month["spent"]); rent = float(month["rent"]); saved = float(month["saved"])
    remaining = available_budget(user_id); days = days_left_in_month(); daily = daily_limit(user_id); spent_today = daily_expenses(user_id); left_today = daily - spent_today
    start = financial_period_start(); end = financial_period_end()
    stats = current_period_stats(user_id)
    goal = get_goal(user_id)
    goal_line = ""
    if goal:
        target, target_date = goal
        need = max(0, target - savings)
        days_to_goal = max(1, (target_date - date.today()).days)
        goal_line = f"\n🎯 Цель: {money(target)} ₽ к {target_date:%d.%m.%Y}\n   Осталось накопить: {money(need)} ₽ · {money(need/days_to_goal)} ₽/день"
    forecast = max(0, stats["forecast"])
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
