from datetime import datetime

from database import db
from database.db import get_connection
from database.income_posting import post_income
from database.periods import ensure_month, month_key
from database.users import ensure_user


def list_planned_income(user_id):
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT p.*,s.name source_name,s.active source_active,"
            "COALESCE(s.withholding_percent,0) withholding_percent "
            "FROM expected_income p LEFT JOIN income_sources s ON s.id=p.source_id AND s.user_id=p.user_id "
            "WHERE p.user_id=? AND p.status='planned' ORDER BY p.due_date,p.id", (user_id,),
        ).fetchall()
    items = []
    for row in rows:
        item = dict(row)
        item["net"] = round(float(item["amount"]) * (1 - float(item["withholding_percent"]) / 100), 2)
        item["source_available"] = item["source_id"] is None or bool(item["source_active"])
        items.append(item)
    return items


def save_planned_income(user_id, title, amount, due_date, source_id=None, plan_id=None):
    ensure_user(user_id)
    title = " ".join(title.split())[:80]
    if not title or not 0 < amount <= 1_000_000_000:
        raise ValueError("Укажите название и положительную сумму")
    with get_connection() as conn:
        if source_id is not None and not conn.execute(
            "SELECT 1 FROM income_sources WHERE id=? AND user_id=? AND active=1", (source_id, user_id),
        ).fetchone():
            raise ValueError("Источник дохода не найден")
        values = (title, round(amount, 2), due_date.isoformat(), source_id, user_id)
        if plan_id is None:
            conn.execute(
                "INSERT INTO expected_income(title,amount,due_date,source_id,user_id) VALUES (?,?,?,?,?)", values,
            )
        else:
            cursor = conn.execute(
                "UPDATE expected_income SET title=?,amount=?,due_date=?,source_id=? "
                "WHERE user_id=? AND id=? AND status='planned'", (*values, plan_id),
            )
            if cursor.rowcount != 1:
                raise ValueError("Поступление уже подтверждено или удалено")


def cancel_planned_income(user_id, plan_id):
    with get_connection() as conn:
        conn.execute("UPDATE expected_income SET status='cancelled' WHERE user_id=? AND id=? AND status='planned'", (user_id, plan_id))


def confirm_planned_income(user_id, plan_id):
    ensure_month(user_id)
    key = month_key(user_id)
    with get_connection() as conn:
        if not db.DATABASE_URL:
            conn.execute("BEGIN IMMEDIATE")
        lock = " FOR UPDATE" if db.DATABASE_URL else ""
        plan = conn.execute("SELECT * FROM expected_income WHERE user_id=? AND id=?" + lock, (user_id, plan_id)).fetchone()
        if not plan or plan["status"] == "cancelled":
            raise ValueError("Поступление не найдено")
        if plan["status"] == "received":
            return False
        _, _, created, transaction_id = post_income(conn, user_id, float(plan["amount"]), plan["title"], key, plan["source_id"], f"planned-income-{plan_id}")
        if not created:
            raise ValueError("Это поступление уже учтено")
        conn.execute("UPDATE expected_income SET status='received',confirmed_at=?,confirmed_transaction_id=? WHERE user_id=? AND id=?", (datetime.now().isoformat(timespec="seconds"), transaction_id, user_id, plan_id))
        return True
