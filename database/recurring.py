from calendar import monthrange
from datetime import date
from database.db import get_connection
from database.operations import add_recurring_charge
from database.users import ensure_user


def list_recurring_payments(user_id: int):
    ensure_user(user_id)
    with get_connection() as conn:
        return conn.execute(
            "SELECT id, title, amount, kind, day_of_month, active, last_run, last_notified "
            "FROM recurring_payments WHERE user_id=? ORDER BY day_of_month, id",
            (user_id,),
        ).fetchall()


def add_recurring_payment(user_id: int, title: str, amount: float, kind: str, day_of_month: int):
    if kind not in {"expense", "rent"}:
        raise ValueError("Некорректный тип регулярного платежа")
    if not 1 <= day_of_month <= 28:
        raise ValueError("День платежа должен быть от 1 до 28")
    ensure_user(user_id)
    today = date.today()
    # A newly created rule starts from its next occurrence. Mark the current
    # month handled when its configured day has already arrived.
    last_run = today.isoformat() if day_of_month <= today.day else None
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO recurring_payments(user_id, title, amount, kind, day_of_month, last_run) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, title[:255], round(amount, 2), kind, day_of_month, last_run),
        )


def delete_recurring_payment(user_id: int, payment_id: int):
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM recurring_payments WHERE user_id=? AND id=?",
            (user_id, payment_id),
        )


def due_recurring_notifications(today: date | None = None):
    today = today or date.today()
    period_key = today.strftime("%Y-%m")
    with get_connection() as conn:
        return conn.execute(
            "SELECT id, user_id, title, amount, kind, day_of_month, last_run "
            "FROM recurring_payments WHERE active=1 AND day_of_month=? "
            "AND (last_notified IS NULL OR last_notified NOT LIKE ?)",
            (today.day, f"{period_key}%"),
        ).fetchall()


def mark_recurring_notified(payment_id: int, today: date | None = None):
    today = today or date.today()
    with get_connection() as conn:
        conn.execute(
            "UPDATE recurring_payments SET last_notified=? WHERE id=?",
            (today.isoformat(), payment_id),
        )


def apply_due_recurring_payments(user_id: int, today: date | None = None):
    today = today or date.today()
    period_key = today.strftime("%Y-%m")
    payments = list_recurring_payments(user_id)
    applied = []
    for payment in payments:
        if not int(payment["active"]):
            continue
        due_day = min(int(payment["day_of_month"]), monthrange(today.year, today.month)[1])
        if today.day < due_day or (payment["last_run"] or "").startswith(period_key):
            continue
        request_id = f"recurring-{payment['id']}-{period_key}"
        success = add_recurring_charge(
            user_id, float(payment["amount"]), payment["title"], request_id
        )
        if not success:
            continue
        with get_connection() as conn:
            conn.execute(
                "UPDATE recurring_payments SET last_run=? WHERE user_id=? AND id=?",
                (today.isoformat(), user_id, payment["id"]),
            )
        applied.append(int(payment["id"]))
    return applied
