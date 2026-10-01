from datetime import date, datetime
from database.db import get_connection
from database.users import ensure_user

DEFAULT_FINANCIAL_DAY = 20


def get_financial_day(user_id: int) -> int:

    ensure_user(user_id)
    with get_connection() as conn:
        row = conn.execute("SELECT financial_day FROM users WHERE user_id=?", (user_id,)).fetchone()
    return int(row["financial_day"] or DEFAULT_FINANCIAL_DAY)


def set_financial_day(user_id: int, financial_day: int):
    if not 1 <= financial_day <= 28:
        raise ValueError("День начала периода должен быть от 1 до 28.")
    ensure_user(user_id)
    with get_connection() as conn:
        conn.execute("UPDATE users SET financial_day=? WHERE user_id=?", (financial_day, user_id))
    # The new current period may have a different key. Rebuild only its summary
    # from immutable transaction history, leaving all prior periods untouched.
    rebuild_month_from_transactions(user_id, financial_period_start(user_id))


def financial_period_start(user_id: int, dt=None) -> date:
    dt = dt or datetime.now()
    financial_day = get_financial_day(user_id)
    return financial_period_start_for_day(financial_day, dt)


def financial_period_start_for_day(financial_day: int, dt=None) -> date:
    dt = dt or datetime.now()
    if dt.day >= financial_day:
        return date(dt.year, dt.month, financial_day)
    if dt.month == 1:
        return date(dt.year - 1, 12, financial_day)
    return date(dt.year, dt.month - 1, financial_day)


def financial_period_end(user_id: int, dt=None) -> date:
    start = financial_period_start(user_id, dt)
    return financial_period_end_for_start(start)


def financial_period_end_for_start(start: date) -> date:
    if start.month == 12:
        return date(start.year + 1, 1, start.day)
    return date(start.year, start.month + 1, start.day)


def month_key(user_id: int, dt=None):
    return financial_period_start(user_id, dt).isoformat()


def ensure_month(user_id: int, key=None):
    key = key or month_key(user_id)
    ensure_user(user_id)
    with get_connection() as conn:
        conn.execute("INSERT OR IGNORE INTO months(user_id, month) VALUES (?, ?)", (user_id, key))


def get_month(user_id: int, key=None):
    key = key or month_key(user_id)
    ensure_month(user_id, key)
    with get_connection() as conn:
        return conn.execute("SELECT * FROM months WHERE user_id=? AND month=?", (user_id, key)).fetchone()


def rebuild_month_from_transactions(user_id: int, start: date):
    end = financial_period_end(user_id, start)
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT kind, amount FROM transactions WHERE user_id=? AND created_at>=? AND created_at<?",
            (user_id, start.isoformat(), end.isoformat()),
        ).fetchall()
        totals = {"income": 0.0, "mandatory": 0.0, "expense": 0.0, "recurring": 0.0, "account_transfer": 0.0, "account_return": 0.0, "rent": 0.0, "save": 0.0}
        for row in rows:
            if row["kind"] in totals:
                totals[row["kind"]] += float(row["amount"])
        conn.execute("INSERT OR IGNORE INTO months(user_id, month) VALUES (?, ?)", (user_id, start.isoformat()))
        conn.execute(
            "UPDATE months SET budget=?, spent=?, rent=?, saved=? WHERE user_id=? AND month=?",
            (
                round(totals["income"] - totals["mandatory"], 2),
                round(totals["expense"] + totals["recurring"] + totals["account_transfer"] - totals["account_return"], 2),
                round(totals["rent"], 2),
                round(totals["save"], 2),
                user_id,
                start.isoformat(),
            ),
        )
