from collections import defaultdict
from datetime import date, timedelta
from database.db import get_connection
from database.repository import financial_period_start, financial_period_end, get_month, get_savings

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
    daily = defaultdict(float)
    income = mandatory = rent = saved = expenses = 0.0
    for r in rows:
        amount = float(r["amount"])
        kind = r["kind"]
        if kind == "expense":
            expenses += amount
            categories[r["description"]] += amount
            daily[r["created_at"][:10]] += amount
        elif kind == "income": income += amount
        elif kind == "mandatory": mandatory += amount
        elif kind == "rent": rent += amount
        elif kind == "save": saved += amount
    days_elapsed = max(1, (date.today() - start).days + 1)
    days_total = max(1, (end - start).days)
    avg = expenses / days_elapsed
    remaining = float(month["budget"]) - expenses - rent - saved
    forecast = remaining - max(0, avg) * max(0, (end - date.today()).days)
    return {
        "start": start, "end": end, "income": income, "mandatory": mandatory,
        "expenses": expenses, "rent": rent, "saved": saved, "remaining": remaining,
        "avg": avg, "forecast": forecast, "days_elapsed": days_elapsed,
        "days_total": days_total, "categories": dict(categories), "daily": dict(daily),
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
