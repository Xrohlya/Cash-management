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
    from database.openings import available, lock_period_user
    if not 1 <= financial_day <= 28:
        raise ValueError("День начала периода должен быть от 1 до 28.")
    ensure_user(user_id)
    ensure_month(user_id)
    with get_connection() as conn:
        lock_period_user(conn, user_id)
        user = conn.execute("SELECT financial_day FROM users WHERE user_id=?", (user_id,)).fetchone()
        if int(user["financial_day"]) == financial_day:
            return
        old_key = financial_period_start_for_day(int(user["financial_day"])).isoformat()
        old = conn.execute("SELECT * FROM months WHERE user_id=? AND month=?", (user_id, old_key)).fetchone()
        start = financial_period_start_for_day(financial_day)
        end = financial_period_end_for_start(start)
        totals = period_totals(conn, user_id, start, end)
        spent = totals["expense"] + totals["recurring"] + totals["account_transfer"] - totals["account_return"]
        net = totals["income"] - totals["mandatory"]
        opening = round(available(old) - (net - spent - totals["rent"] - totals["save"]), 2)
        conn.execute("UPDATE users SET financial_day=? WHERE user_id=?", (financial_day, user_id))
        conn.execute("INSERT OR IGNORE INTO months(user_id,month) VALUES (?,?)", (user_id, start.isoformat()))
        conn.execute("INSERT INTO period_openings(user_id,month,source_month,amount,created_at) VALUES (?,?,NULL,?,?) ON CONFLICT(user_id,month) DO UPDATE SET source_month=NULL,amount=excluded.amount",
                     (user_id, start.isoformat(), opening, datetime.now().isoformat(timespec="seconds")))
        conn.execute("UPDATE months SET budget=?,spent=?,rent=?,saved=? WHERE user_id=? AND month=?",
                     (round(net + opening, 2), round(spent, 2), totals["rent"], totals["save"], user_id, start.isoformat()))


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


def ensure_month(user_id: int, key=None, *, today=None):
    from database.openings import initialise_opening, lock_period_user

    active_key = month_key(user_id, today)
    key = key or active_key
    with get_connection() as conn:
        ready = conn.execute(
            "SELECT 1 FROM months m WHERE m.user_id=? AND m.month=? "
            "AND (?<>? OR EXISTS (SELECT 1 FROM period_openings o WHERE o.user_id=m.user_id AND o.month=m.month))",
            (user_id, key, key, active_key),
        ).fetchone()
    if ready:
        return
    ensure_user(user_id)
    with get_connection() as conn:
        lock_period_user(conn, user_id)
        conn.execute("INSERT OR IGNORE INTO months(user_id, month) VALUES (?, ?)", (user_id, key))
        if key == active_key:
            initialise_opening(conn, user_id, key)


def get_month(user_id: int, key=None):
    key = key or month_key(user_id)
    ensure_month(user_id, key)
    with get_connection() as conn:
        return conn.execute("SELECT * FROM months WHERE user_id=? AND month=?", (user_id, key)).fetchone()


def period_totals(conn, user_id, start, end):
    rows = conn.execute("SELECT kind,amount FROM transactions WHERE user_id=? AND created_at>=? AND created_at<?",
                        (user_id, start.isoformat(), end.isoformat())).fetchall()
    totals = dict.fromkeys(("income", "mandatory", "expense", "recurring", "account_transfer", "account_return", "rent", "save"), 0.0)
    for row in rows:
        if row["kind"] in totals:
            totals[row["kind"]] += float(row["amount"])
    return totals


def rebuild_month_from_transactions(user_id: int, start: date):
    from database.openings import opening_amount, require_unclosed_period, lock_period_user
    end = financial_period_end(user_id, start)
    with get_connection() as conn:
        lock_period_user(conn, user_id)
        require_unclosed_period(conn, user_id, start.isoformat())
        totals = period_totals(conn, user_id, start, end)
        conn.execute("INSERT OR IGNORE INTO months(user_id, month) VALUES (?, ?)", (user_id, start.isoformat()))
        conn.execute(
            "UPDATE months SET budget=?, spent=?, rent=?, saved=? WHERE user_id=? AND month=?",
            (
                round(totals["income"] - totals["mandatory"] + opening_amount(conn, user_id, start.isoformat()), 2),
                round(totals["expense"] + totals["recurring"] + totals["account_transfer"] - totals["account_return"], 2),
                round(totals["rent"], 2),
                round(totals["save"], 2),
                user_id,
                start.isoformat(),
            ),
        )
