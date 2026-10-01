from collections import defaultdict
from calendar import monthrange
from datetime import date, timedelta
from database.db import get_connection
from database.repository import (
    financial_period_end,
    financial_period_start,
    get_month,
    get_savings,
    normalize_expense_category,
)

def set_goal(user_id: int, target: float, target_date: date):
    with get_connection() as conn:
        conn.execute("DELETE FROM goals WHERE user_id=?", (user_id,))
        conn.execute(
            "INSERT INTO goals(user_id, target, target_date) VALUES (?, ?, ?)",
            (user_id, round(target, 2), target_date.isoformat()),
        )


def get_goal(user_id: int):
    with get_connection() as conn:
        item = conn.execute(
            "SELECT target, target_date FROM goals WHERE user_id=?", (user_id,)
        ).fetchone()
    if not item:
        return None
    try:
        return float(item["target"]), date.fromisoformat(item["target_date"])
    except Exception:
        return None


def clear_goal(user_id: int):
    with get_connection() as conn:
        conn.execute("DELETE FROM goals WHERE user_id=?", (user_id,))


def current_period_stats(user_id: int):
    start = financial_period_start(user_id)
    end = financial_period_end(user_id)
    month = get_month(user_id)
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT created_at, kind, amount, description FROM transactions "
            "WHERE user_id=? AND created_at>=? AND created_at<? ORDER BY created_at",
            (user_id, start.isoformat(), end.isoformat()),
        ).fetchall()
    categories = defaultdict(float)
    category_counts = defaultdict(int)
    daily = defaultdict(float)
    income = mandatory = rent = saved = expenses = recurring = transferred = returned = 0.0
    for r in rows:
        amount = float(r["amount"])
        kind = r["kind"]
        if kind == "expense":
            expenses += amount
            category = normalize_expense_category(r["description"])
            categories[category] += amount
            category_counts[category] += 1
            daily[r["created_at"][:10]] += amount
        elif kind == "income": income += amount
        elif kind == "mandatory": mandatory += amount
        elif kind == "rent": rent += amount
        elif kind == "recurring": recurring += amount
        elif kind == "save": saved += amount
        elif kind == "account_transfer": transferred += amount
        elif kind == "account_return": returned += amount
    days_elapsed = max(1, (date.today() - start).days + 1)
    days_total = max(1, (end - start).days)
    avg = expenses / days_elapsed
    remaining = float(month["budget"]) - expenses - recurring - transferred + returned - rent - saved
    forecast = remaining - max(0, avg) * max(0, (end - date.today()).days)
    return {
        "start": start, "end": end, "income": income, "mandatory": mandatory,
        "expenses": expenses, "recurring": recurring, "transferred": transferred, "returned": returned,
        "rent": rent, "saved": saved, "remaining": remaining,
        "avg": avg, "forecast": forecast, "days_elapsed": days_elapsed,
        "days_total": days_total, "categories": dict(categories),
        "category_counts": dict(category_counts), "daily": dict(daily),
        "savings_total": get_savings(user_id),
    }


def comparison(user_id: int):
    current = current_period_stats(user_id)
    previous_day = current["start"] - timedelta(days=1)
    prev_start = financial_period_start(user_id, previous_day)
    prev_end = current["start"]
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COALESCE(SUM(amount),0) total FROM transactions "
            "WHERE user_id=? AND kind='expense' AND created_at>=? AND created_at<?",
            (user_id, prev_start.isoformat(), prev_end.isoformat()),
        ).fetchone()
    previous = float(row["total"] or 0)
    return current["expenses"], previous


def _monthly_occurrences(day_of_month: int, start: date, end: date):
    cursor = date(start.year, start.month, 1)
    result = []
    while cursor < end:
        due = date(cursor.year, cursor.month, min(day_of_month, monthrange(cursor.year, cursor.month)[1]))
        if start <= due < end:
            result.append(due)
        cursor = date(cursor.year + (cursor.month == 12), 1 if cursor.month == 12 else cursor.month + 1, 1)
    return result


def financial_radar(
    user_id: int,
    remaining: float,
    recurring_payments: list,
    today: date | None = None,
    target_balance: float = 0,
    period: tuple[date, date] | None = None,
):
    today = today or date.today()
    if period is None:
        start = financial_period_start(user_id, today)
        from database.repository import financial_period_end_for_start
        end = financial_period_end_for_start(start)
    else:
        start, end = period
    upcoming = []
    for payment in recurring_payments:
        if not int(payment["active"]):
            continue
        last_run = date.fromisoformat(payment["last_run"][:10]) if payment["last_run"] else None
        for due in _monthly_occurrences(int(payment["day_of_month"]), today, end):
            if last_run and last_run.year == due.year and last_run.month == due.month:
                continue
            upcoming.append({
                "date": due.isoformat(),
                "title": payment["title"],
                "amount": round(float(payment["amount"]), 2),
                "kind": "payment",
            })
    upcoming.sort(key=lambda item: (item["date"], item["title"]))
    reserved = round(sum(item["amount"] for item in upcoming), 2)

    with get_connection() as conn:
        spend_rows = conn.execute(
            "SELECT created_at,kind,amount,description FROM transactions "
            "WHERE user_id=? AND kind IN ('expense','recurring','rent') ORDER BY created_at",
            (user_id,),
        ).fetchall()
        income_rows = conn.execute(
            "SELECT created_at,amount,description FROM transactions "
            "WHERE user_id=? AND kind='income' AND created_at>=? AND created_at<? ORDER BY created_at DESC",
            (user_id, start.isoformat(), (today + timedelta(days=1)).isoformat()),
        ).fetchall()

    spend_dates = {date.fromisoformat(row["created_at"][:10]) for row in spend_rows}
    first_activity = min(spend_dates) if spend_dates else today
    current_streak = 0
    cursor = today
    while cursor >= first_activity and cursor not in spend_dates:
        current_streak += 1
        cursor -= timedelta(days=1)

    best_streak = 0
    running = 0
    cursor = first_activity
    while cursor <= today:
        if cursor in spend_dates:
            running = 0
        else:
            running += 1
            best_streak = max(best_streak, running)
        cursor += timedelta(days=1)

    this_week_start = today - timedelta(days=6)
    previous_week_start = today - timedelta(days=13)
    this_week = previous_week = 0.0
    for row in spend_rows:
        transaction_day = date.fromisoformat(row["created_at"][:10])
        amount = float(row["amount"])
        if this_week_start <= transaction_day <= today:
            this_week += amount
        elif previous_week_start <= transaction_day < this_week_start:
            previous_week += amount
    if previous_week > 0:
        weekly_change = round((this_week - previous_week) / previous_week * 100, 1)
    elif this_week > 0:
        weekly_change = 100.0
    else:
        weekly_change = 0.0

    days_left = max(1, (end - today).days)
    target_balance = max(0.0, float(target_balance))
    safe_today = max(0.0, (float(remaining) - reserved - target_balance) / days_left)
    elapsed = max(1, (today - start).days + 1)
    period_spending = sum(
        float(row["amount"])
        for row in spend_rows
        if row["kind"] == "expense"
        and start <= date.fromisoformat(row["created_at"][:10]) <= today
    )
    daily_pace = period_spending / elapsed
    projected_balance = float(remaining) - reserved - daily_pace * max(0, days_left - 1)
    target_gap = projected_balance - target_balance
    if target_gap < 0:
        risk = "red"
        risk_title = "Высокий риск"
        risk_text = "При текущем темпе желаемый остаток не сохранится."
    elif target_gap < max(500, float(remaining) * 0.15):
        risk = "yellow"
        risk_title = "Нужна осторожность"
        risk_text = "Запас к концу периода будет небольшим."
    else:
        risk = "green"
        risk_title = "Всё под контролем"
        risk_text = "Текущий темп укладывается в бюджет."

    calendar_events = upcoming[:8]
    for row in income_rows[:4]:
        calendar_events.append({
            "date": row["created_at"][:10],
            "title": row["description"] or "Доход",
            "amount": round(float(row["amount"]), 2),
            "kind": "income",
        })
    calendar_events.append({
        "date": (end - timedelta(days=1)).isoformat(),
        "title": "Конец финансового периода",
        "amount": 0,
        "kind": "period",
    })
    calendar_events.sort(key=lambda item: (item["date"], item["kind"] != "income"))

    return {
        "safe_today": round(safe_today, 2),
        "reserved": reserved,
        "projected_balance": round(projected_balance, 2),
        "target_balance": round(target_balance, 2),
        "risk": risk,
        "risk_title": risk_title,
        "risk_text": risk_text,
        "calendar": calendar_events,
        "streak": {"current": current_streak, "best": best_streak},
        "weekly": {
            "current": round(this_week, 2),
            "previous": round(previous_week, 2),
            "change_percent": weekly_change,
        },
    }
