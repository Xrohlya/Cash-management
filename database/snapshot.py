from datetime import date, timedelta
from config.settings import DEFAULT_MANDATORY_PERCENT
from database import db
from database.db import get_connection
from database.periods import DEFAULT_FINANCIAL_DAY, financial_period_end_for_start, financial_period_start_for_day
from database.recurring import apply_due_recurring_payments
from database.users import ensure_user


def get_status_snapshot(user_id: int, today: date | None = None) -> dict:
    today = today or date.today()
    apply_due_recurring_payments(user_id, today)
    if db.DATABASE_URL:
        with get_connection() as conn:
            row = conn.execute(
                """
                WITH ins_user AS (
                    INSERT INTO users(user_id, mandatory_percent)
                    VALUES (?, ?)
                    ON CONFLICT (user_id) DO NOTHING
                ),
                u AS (
                    SELECT mandatory_percent, financial_day, target_balance, savings, status_chat_id, status_message_id
                    FROM users
                    WHERE user_id=?
                ),
                period AS (
                    SELECT
                        u.*,
                        CASE
                            WHEN EXTRACT(DAY FROM ?::date)::int >= u.financial_day THEN
                                make_date(EXTRACT(YEAR FROM ?::date)::int, EXTRACT(MONTH FROM ?::date)::int, u.financial_day)
                            ELSE
                                make_date(
                                    EXTRACT(YEAR FROM (?::date - INTERVAL '1 month'))::int,
                                    EXTRACT(MONTH FROM (?::date - INTERVAL '1 month'))::int,
                                    u.financial_day
                                )
                        END AS start_date
                    FROM u
                ),
                ins_month AS (
                    INSERT INTO months(user_id, month)
                    SELECT ?, start_date::text FROM period
                    ON CONFLICT (user_id, month) DO NOTHING
                    RETURNING 1
                ),
                m AS (
                    SELECT months.budget, months.spent, months.rent, months.saved
                    FROM months, period
                    WHERE months.user_id=? AND months.month=period.start_date::text
                ),
                d AS (
                    SELECT COALESCE(SUM(amount), 0) AS spent_today
                    FROM transactions
                    WHERE user_id=? AND kind='expense' AND created_at>=? AND created_at<?
                ),
                g AS (
                    SELECT target, target_date FROM goals WHERE user_id=?
                )
                SELECT
                    period.mandatory_percent,
                    period.financial_day,
                    period.target_balance,
                    period.savings,
                    period.status_chat_id,
                    period.status_message_id,
                    period.start_date::text AS start_date,
                    m.budget,
                    m.spent,
                    m.rent,
                    m.saved,
                    d.spent_today,
                    g.target,
                    g.target_date,
                    (SELECT COUNT(*) FROM ins_month) AS inserted_months
                FROM period
                CROSS JOIN m
                CROSS JOIN d
                LEFT JOIN g ON TRUE
                """,
                (
                    user_id,
                    DEFAULT_MANDATORY_PERCENT,
                    user_id,
                    today.isoformat(),
                    today.isoformat(),
                    today.isoformat(),
                    today.isoformat(),
                    today.isoformat(),
                    user_id,
                    user_id,
                    user_id,
                    today.isoformat(),
                    (today + timedelta(days=1)).isoformat(),
                    user_id,
                ),
            ).fetchone()
        start = date.fromisoformat(row["start_date"])
        end = financial_period_end_for_start(start)
        budget = float(row["budget"])
        total_spent = float(row["spent"])
        with get_connection() as conn:
            special_row = conn.execute(
                "SELECT "
                "COALESCE(SUM(CASE WHEN kind='recurring' THEN amount ELSE 0 END),0) recurring,"
                "COALESCE(SUM(CASE WHEN kind='account_transfer' THEN amount ELSE 0 END),0) transferred,"
                "COALESCE(SUM(CASE WHEN kind='account_return' THEN amount ELSE 0 END),0) returned "
                "FROM transactions WHERE user_id=? AND created_at>=? AND created_at<?",
                (user_id, start.isoformat(), end.isoformat()),
            ).fetchone()
        recurring = float(special_row["recurring"] or 0)
        transferred = float(special_row["transferred"] or 0)
        returned = float(special_row["returned"] or 0)
        spent = total_spent - recurring - transferred + returned
        rent = float(row["rent"])
        saved = float(row["saved"])
        savings = float(row["savings"])
        remaining = budget - total_spent - rent - saved
        days_left = max(0, (end - today).days)
        days_elapsed = max(1, (today - start).days + 1)
        avg = spent / days_elapsed
        forecast = remaining - max(0, avg) * max(0, (end - today).days)
        goal = None
        if row["target"] is not None and row["target_date"] is not None:
            goal = {"target": row["target"], "target_date": row["target_date"]}
        return {
            "start": start,
            "end": end,
            "financial_day": int(row["financial_day"] or DEFAULT_FINANCIAL_DAY),
            "target_balance": float(row["target_balance"] or 0),
            "mandatory_percent": float(row["mandatory_percent"]),
            "budget": budget,
            "spent": spent,
            "recurring": recurring,
            "rent": rent,
            "saved": saved,
            "savings": savings,
            "remaining": remaining,
            "days_left": days_left,
            "daily_limit": remaining / days_left if days_left else remaining,
            "spent_today": float(row["spent_today"] or 0),
            "forecast": forecast,
            "goal": goal,
            "status_message": (
                (int(row["status_chat_id"]), int(row["status_message_id"]))
                if row["status_chat_id"] is not None and row["status_message_id"] is not None
                else None
            ),
        }

    ensure_user(user_id)
    with get_connection() as conn:
        user = conn.execute(
            "SELECT mandatory_percent, financial_day, target_balance, savings, status_chat_id, status_message_id "
            "FROM users WHERE user_id=?",
            (user_id,),
        ).fetchone()
        financial_day = int(user["financial_day"] or DEFAULT_FINANCIAL_DAY)
        start = financial_period_start_for_day(financial_day, today)
        end = financial_period_end_for_start(start)
        key = start.isoformat()
        conn.execute("INSERT OR IGNORE INTO months(user_id, month) VALUES (?, ?)", (user_id, key))
        month = conn.execute(
            "SELECT budget, spent, rent, saved FROM months WHERE user_id=? AND month=?",
            (user_id, key),
        ).fetchone()
        daily_row = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) AS total FROM transactions "
            "WHERE user_id=? AND kind='expense' AND created_at>=? AND created_at<?",
            (user_id, today.isoformat(), (today + timedelta(days=1)).isoformat()),
        ).fetchone()
        special_row = conn.execute(
            "SELECT "
            "COALESCE(SUM(CASE WHEN kind='recurring' THEN amount ELSE 0 END),0) recurring,"
            "COALESCE(SUM(CASE WHEN kind='account_transfer' THEN amount ELSE 0 END),0) transferred,"
            "COALESCE(SUM(CASE WHEN kind='account_return' THEN amount ELSE 0 END),0) returned "
            "FROM transactions WHERE user_id=? AND created_at>=? AND created_at<?",
            (user_id, start.isoformat(), end.isoformat()),
        ).fetchone()
        goal = conn.execute(
            "SELECT target, target_date FROM goals WHERE user_id=?",
            (user_id,),
        ).fetchone()

    budget = float(month["budget"])
    total_spent = float(month["spent"])
    recurring = float(special_row["recurring"] or 0)
    transferred = float(special_row["transferred"] or 0)
    returned = float(special_row["returned"] or 0)
    spent = total_spent - recurring - transferred + returned
    rent = float(month["rent"])
    saved = float(month["saved"])
    savings = float(user["savings"])
    remaining = budget - total_spent - rent - saved
    days_left = max(0, (end - today).days)
    days_elapsed = max(1, (today - start).days + 1)
    avg = spent / days_elapsed
    forecast = remaining - max(0, avg) * max(0, (end - today).days)
    return {
        "start": start,
        "end": end,
        "financial_day": financial_day,
        "target_balance": float(user["target_balance"] or 0),
        "mandatory_percent": float(user["mandatory_percent"]),
        "budget": budget,
        "spent": spent,
        "recurring": recurring,
        "rent": rent,
        "saved": saved,
        "savings": savings,
        "remaining": remaining,
        "days_left": days_left,
        "daily_limit": remaining / days_left if days_left else remaining,
        "spent_today": float(daily_row["total"] or 0),
        "forecast": forecast,
        "goal": goal,
        "status_message": (
            (int(user["status_chat_id"]), int(user["status_message_id"]))
            if user["status_chat_id"] is not None and user["status_message_id"] is not None
            else None
        ),
    }
