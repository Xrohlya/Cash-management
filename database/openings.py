"""Opening balances are period funds, never income or savings."""
from datetime import date, datetime

from database import db
from database.db import get_connection


def create_opening_schema(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS period_openings (
        user_id BIGINT NOT NULL, month TEXT NOT NULL,
        source_month TEXT, amount DOUBLE PRECISION NOT NULL,
        created_at TEXT NOT NULL,
        PRIMARY KEY(user_id,month), UNIQUE(user_id,source_month)
    )""")


def lock_period_user(conn, user_id):
    if not db.DATABASE_URL:
        conn.execute("BEGIN IMMEDIATE")
    suffix = " FOR UPDATE" if db.DATABASE_URL else ""
    conn.execute("SELECT user_id FROM users WHERE user_id=?" + suffix, (user_id,)).fetchone()


def available(row):
    return round(float(row["budget"]) - float(row["spent"]) - float(row["rent"]) - float(row["saved"]), 2)


def initialise_opening(conn, user_id, key):
    from database.periods import financial_period_end_for_start

    if conn.execute("SELECT 1 FROM period_openings WHERE user_id=? AND month=?", (user_id, key)).fetchone():
        return
    previous = conn.execute("SELECT * FROM months WHERE user_id=? AND month<? AND substr(month,9,2)=substr(?,9,2) ORDER BY month DESC LIMIT 1", (user_id, key, key)).fetchone()
    amount, source = 0.0, None
    if previous is not None:
        end = financial_period_end_for_start(date.fromisoformat(previous["month"]))
        used = conn.execute("SELECT 1 FROM period_openings WHERE user_id=? AND source_month=?", (user_id, previous["month"])).fetchone()
        # Changing period dates can leave overlapping legacy summaries.
        if end <= date.fromisoformat(key) and not used:
            amount, source = available(previous), previous["month"]
    conn.execute("INSERT INTO period_openings(user_id,month,source_month,amount,created_at) VALUES (?,?,?,?,?)",
                 (user_id, key, source, amount, datetime.now().isoformat(timespec="seconds")))
    conn.execute("UPDATE months SET budget=budget+? WHERE user_id=? AND month=?", (amount, user_id, key))


def opening_amount(conn, user_id, key):
    row = conn.execute("SELECT amount FROM period_openings WHERE user_id=? AND month=?", (user_id, key)).fetchone()
    return float(row["amount"]) if row is not None else 0.0


def require_unclosed_period(conn, user_id, key):
    from database.periods import financial_period_start_for_day
    user = conn.execute("SELECT financial_day FROM users WHERE user_id=?", (user_id,)).fetchone()
    active_key = financial_period_start_for_day(int(user["financial_day"])).isoformat()
    if key < active_key and conn.execute("SELECT 1 FROM period_openings WHERE user_id=? AND month=?", (user_id, active_key)).fetchone():
        raise ValueError("Этот период закрыт, остаток уже перенесён. Оформите возврат в текущем периоде вместо изменения старого расхода.")


def rollover_all_users(today=None):
    from database.periods import ensure_month, financial_period_start_for_day

    today = today or date.today()
    with get_connection() as conn:
        users = conn.execute("SELECT user_id,financial_day FROM users").fetchall()
    for user in users:
        key = financial_period_start_for_day(int(user["financial_day"]), today).isoformat()
        ensure_month(int(user["user_id"]), key, today=today)
