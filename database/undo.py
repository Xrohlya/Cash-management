"""Atomic cancellation with a complete archive of the original ledger rows."""
import json
from datetime import date, datetime

from database import db
from database.db import get_connection
from database.periods import financial_period_end_for_start, financial_period_start_for_day


def _last_rows(conn, user_id):
    rows = conn.execute(
        "SELECT * FROM transactions WHERE user_id=? AND kind<>'recurring' ORDER BY id DESC LIMIT 2", (user_id,),
    ).fetchall()
    if not rows:
        return []
    last = dict(rows[0])
    if last["kind"] != "mandatory":
        return [last]
    if len(rows) < 2:
        raise ValueError("Нельзя определить доход, к которому относится удержание")
    income = dict(rows[1])
    if income["kind"] != "income" or income["created_at"] != last["created_at"] or income["income_source_id"] != last["income_source_id"]:
        raise ValueError("Доход с удержанием требует отдельной проверки")
    return [income, last]


def undo_candidate(user_id):
    with get_connection() as conn:
        try:
            rows = _last_rows(conn, user_id)
        except ValueError as exc:
            return {"allowed": False, "reason": str(exc)}
    if not rows:
        return None
    original = rows[0]
    return {"id": max(row["id"] for row in rows), "kind": original["kind"],
            "amount": float(original["amount"]), "description": original["description"],
            "created_at": original["created_at"], "allowed": True}


def undo_last_operation(user_id, expected_id):
    with get_connection() as conn:
        if not db.DATABASE_URL:
            conn.execute("BEGIN IMMEDIATE")
        lock = " FOR UPDATE" if db.DATABASE_URL else ""
        user = conn.execute("SELECT financial_day,savings FROM users WHERE user_id=?" + lock, (user_id,)).fetchone()
        if not user:
            raise ValueError("Операция не найдена")
        rows = _last_rows(conn, user_id)
        if not rows or max(row["id"] for row in rows) != expected_id:
            raise ValueError("Список операций изменился. Обновите приложение.")
        original = rows[0]
        start = financial_period_start_for_day(int(user["financial_day"]), date.today())
        end = financial_period_end_for_start(start)
        operation_day = date.fromisoformat(original["created_at"][:10])
        if not start <= operation_day < end:
            raise ValueError("Можно отменить операцию только текущего финансового периода")
        deltas = {"budget": 0.0, "spent": 0.0, "rent": 0.0, "saved": 0.0}
        columns = {"income": ("budget", -1), "mandatory": ("budget", 1), "expense": ("spent", -1),
                   "rent": ("rent", -1), "save": ("saved", -1), "account_transfer": ("spent", -1), "account_return": ("spent", 1)}
        for row in rows:
            if row["kind"] not in columns:
                raise ValueError("Эту операцию нельзя отменить автоматически")
            column, sign = columns[row["kind"]]
            deltas[column] += sign * float(row["amount"])
        account_row = None
        if original["kind"] in {"account_transfer", "account_return"}:
            account_row = _undo_account(conn, user_id, original)
        if original["kind"] == "save":
            changed = conn.execute("UPDATE users SET savings=savings-? WHERE user_id=? AND savings>=?", (original["amount"], user_id, original["amount"]))
            if changed.rowcount != 1:
                raise ValueError("Недостаточно средств в накоплениях для отмены")
        values = tuple(round(deltas[column], 2) for column in ("budget", "spent", "rent", "saved"))
        changed = conn.execute(
            "UPDATE months SET budget=budget+?,spent=spent+?,rent=rent+?,saved=saved+? "
            "WHERE user_id=? AND month=? AND (budget+?-spent-?-rent-?-saved-?)>=-0.005",
            (*values, user_id, start.isoformat(), *values),
        )
        if changed.rowcount != 1:
            raise ValueError("Доход уже потрачен: отмена сделает баланс отрицательным")
        payload = {"transactions": rows, "account_transaction": account_row}
        conn.execute("INSERT INTO operation_undo(user_id,created_at,transaction_id,original_data) VALUES (?,?,?,?)",
                     (user_id, datetime.now().isoformat(timespec="seconds"), expected_id, json.dumps(payload, ensure_ascii=False)))
        for row in rows:
            conn.execute("DELETE FROM transactions WHERE user_id=? AND id=?", (user_id, row["id"]))
        plan = conn.execute("SELECT id FROM expected_income WHERE user_id=? AND confirmed_transaction_id=? AND status='received'", (user_id, original["id"])).fetchone()
        if plan:
            conn.execute("UPDATE expected_income SET status='planned',confirmed_at=NULL,confirmed_transaction_id=NULL WHERE user_id=? AND id=?", (user_id, plan["id"]))
            conn.execute("DELETE FROM operation_requests WHERE user_id=? AND request_id=?", (user_id, f"planned-income-{plan['id']}"))


def _undo_account(conn, user_id, original):
    row = conn.execute("SELECT * FROM account_transactions WHERE user_id=? ORDER BY id DESC LIMIT 1", (user_id,)).fetchone()
    direction = "in" if original["kind"] == "account_transfer" else "out"
    if not row or row["created_at"] != original["created_at"] or row["kind"] != direction or float(row["amount"]) != float(original["amount"]):
        raise ValueError("Нельзя определить дополнительный счёт для отмены перевода")
    delta = -float(row["amount"]) if direction == "in" else float(row["amount"])
    changed = conn.execute("UPDATE extra_accounts SET balance=balance+? WHERE user_id=? AND id=? AND active=1 AND balance+?>=-0.005", (delta, user_id, row["account_id"], delta))
    if changed.rowcount != 1:
        raise ValueError("Дополнительный счёт удалён или его баланс недостаточен")
    conn.execute("DELETE FROM account_transactions WHERE user_id=? AND id=?", (user_id, row["id"]))
    return dict(row)


def recent_undos(user_id, limit=10):
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM operation_undo WHERE user_id=? ORDER BY id DESC LIMIT ?", (user_id, limit)).fetchall()
    result = []
    for row in rows:
        original = json.loads(row["original_data"])["transactions"][0]
        result.append({"id": -int(row["id"]), "created_at": row["created_at"], "kind": "cancelled",
                       "amount": float(original["amount"]), "description": f"Отменено: {original['description']}"})
    return result
