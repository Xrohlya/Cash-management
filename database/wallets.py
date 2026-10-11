"""Atomic transfers, wallet expenses and linked partial refunds."""
import math
from datetime import datetime

from database import db
from database.db import get_connection
from database.operations import _claim_request
from database.periods import ensure_month, month_key
from services.categories import normalize_expense_category


def amount_value(value):
    value = round(float(value), 2)
    if not math.isfinite(value) or not 0 < value <= 1_000_000_000:
        raise ValueError("Введите положительную сумму с точностью до копейки")
    return value


def lock_user(conn, user_id):
    if not db.DATABASE_URL:
        conn.execute("BEGIN IMMEDIATE")
    suffix = " FOR UPDATE" if db.DATABASE_URL else ""
    if not conn.execute("SELECT user_id FROM users WHERE user_id=?" + suffix, (user_id,)).fetchone():
        raise ValueError("Пользователь не найден")


def wallet_name(conn, user_id, wallet):
    if wallet in {"main", "savings"}:
        return "Основной" if wallet == "main" else "Накопления"
    if not wallet.startswith("account:") or not wallet[8:].isdigit():
        raise ValueError("Некорректный счёт")
    row = conn.execute("SELECT name FROM extra_accounts WHERE user_id=? AND id=? AND active=1", (user_id, int(wallet[8:]))).fetchone()
    if not row:
        raise ValueError("Счёт не найден или удалён")
    return row["name"]


def move_balance(conn, user_id, wallet, delta, key):
    wallet_name(conn, user_id, wallet)
    if wallet == "main":
        changed = conn.execute("UPDATE months SET spent=spent-? WHERE user_id=? AND month=? AND budget-spent-rent-saved+?>=-0.005", (delta, user_id, key, delta))
    elif wallet == "savings":
        changed = conn.execute("UPDATE users SET savings=savings+? WHERE user_id=? AND savings+?>=-0.005", (delta, user_id, delta))
    else:
        changed = conn.execute("UPDATE extra_accounts SET balance=balance+? WHERE user_id=? AND id=? AND active=1 AND balance+?>=-0.005", (delta, user_id, int(wallet[8:]), delta))
    if changed.rowcount != 1:
        raise ValueError("Недостаточно средств на выбранном счёте")


def record(conn, user_id, kind, amount, description, operation, source, destination="", original_id=None, timestamp=None, original_data=None):
    row = conn.execute("INSERT INTO transactions(user_id,created_at,kind,amount,description) VALUES (?,?,?,?,?) RETURNING id", (user_id, timestamp or datetime.now().isoformat(timespec="seconds"), kind, amount, description)).fetchone()
    conn.execute("INSERT INTO wallet_entries(transaction_id,user_id,operation,source,destination,original_id,original_data) VALUES (?,?,?,?,?,?,?)", (row["id"], user_id, operation, source, destination, original_id, original_data))
    return row["id"]


def transfer(user_id, source, destination, amount, request_id):
    amount = amount_value(amount)
    if source == destination:
        raise ValueError("Выберите разные счета")
    ensure_month(user_id)
    key = month_key(user_id)
    with get_connection() as conn:
        lock_user(conn, user_id)
        names = [wallet_name(conn, user_id, wallet) for wallet in (source, destination)]
        if not _claim_request(conn, user_id, request_id):
            return
        move_balance(conn, user_id, source, -amount, key)
        move_balance(conn, user_id, destination, amount, key)
        kind = "account_transfer" if source == "main" else "account_return" if destination == "main" else "wallet_transfer"
        record(conn, user_id, kind, amount, " → ".join(names), "transfer", source, destination)


def spend(user_id, wallet, amount, description, request_id):
    amount = amount_value(amount)
    ensure_month(user_id)
    key = month_key(user_id)
    with get_connection() as conn:
        lock_user(conn, user_id)
        wallet_name(conn, user_id, wallet)
        if not _claim_request(conn, user_id, request_id):
            return
        move_balance(conn, user_id, wallet, -amount, key)
        record(conn, user_id, "expense" if wallet == "main" else "wallet_expense", amount, normalize_expense_category(description), "expense", wallet)


def refundable_expenses(user_id):
    with get_connection() as conn:
        return [dict(row) for row in conn.execute("""SELECT t.id,t.created_at,t.description,t.amount,
            COALESCE(w.source,'main') wallet,
            t.amount+COALESCE((SELECT SUM(r.amount) FROM wallet_entries x JOIN transactions r ON r.id=x.transaction_id AND r.user_id=x.user_id WHERE x.user_id=t.user_id AND x.original_id=t.id AND x.operation='refund'),0) refundable
            FROM transactions t LEFT JOIN wallet_entries w ON w.transaction_id=t.id AND w.user_id=t.user_id
            WHERE t.user_id=? AND t.kind IN ('expense','wallet_expense') AND t.amount>0
            ORDER BY t.id DESC""", (user_id,)).fetchall() if float(row["refundable"]) > 0.005]


def refund(user_id, original_id, amount, request_id):
    amount = amount_value(amount)
    ensure_month(user_id)
    key = month_key(user_id)
    with get_connection() as conn:
        lock_user(conn, user_id)
        if not _claim_request(conn, user_id, request_id):
            return
        original = conn.execute("SELECT t.*,COALESCE(w.source,'main') wallet FROM transactions t LEFT JOIN wallet_entries w ON w.transaction_id=t.id AND w.user_id=t.user_id WHERE t.user_id=? AND t.id=? AND t.kind IN ('expense','wallet_expense') AND t.amount>0", (user_id, original_id)).fetchone()
        if not original:
            raise ValueError("Исходный расход не найден")
        returned = conn.execute("SELECT COALESCE(SUM(t.amount),0) total FROM wallet_entries w JOIN transactions t ON t.id=w.transaction_id AND t.user_id=w.user_id WHERE w.user_id=? AND w.original_id=? AND w.operation='refund'", (user_id, original_id)).fetchone()
        if amount > round(float(original["amount"]) + float(returned["total"]), 2):
            raise ValueError("Возврат превышает оставшуюся сумму покупки")
        move_balance(conn, user_id, original["wallet"], amount, key)
        record(conn, user_id, original["kind"], -amount, original["description"], "refund", original["wallet"], original_id=original_id)
