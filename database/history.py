from datetime import date, timedelta
from database.db import get_connection
from database.periods import financial_period_start


def daily_expenses(user_id: int, day=None) -> float:
    day = day or date.today()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) AS total FROM transactions "
            "WHERE user_id=? AND kind='expense' AND created_at>=? AND created_at<?",
            (user_id, day.isoformat(), (day + timedelta(days=1)).isoformat()),
        ).fetchone()
        return float(row["total"] or 0)


def daily_expense_transactions(user_id: int, day=None):
    day = day or date.today()
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM transactions WHERE user_id=? AND kind='expense' "
            "AND created_at>=? AND created_at<? ORDER BY id DESC",
            (user_id, day.isoformat(), (day + timedelta(days=1)).isoformat()),
        ).fetchall()


def average_daily_expense(user_id: int, day=None) -> float:

    day = day or date.today()
    start = financial_period_start(user_id, day)
    days_elapsed = (day - start).days + 1
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) AS total FROM transactions "
            "WHERE user_id=? AND kind='expense' AND created_at>=? AND created_at<?",
            (user_id, start.isoformat(), (day + timedelta(days=1)).isoformat()),
        ).fetchone()
    return float(row["total"] or 0) / max(1, days_elapsed)


def recent_transactions(user_id: int, limit=15):
    safe_limit = max(1, min(int(limit), 100))
    with get_connection() as conn:
        return conn.execute(
            "SELECT id, created_at, kind, amount, description FROM transactions "
            "WHERE user_id=? ORDER BY id DESC LIMIT ?",
            (user_id, safe_limit),
        ).fetchall()
