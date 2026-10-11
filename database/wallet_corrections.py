"""Explicit audited correction of an income mistakenly entered as a refund."""
import json
from datetime import datetime

from database.db import get_connection
from database.periods import financial_period_start_for_day
from database.wallets import lock_user, amount_value


def correct_income_as_refund(user_id, income_id, expected_amount, expense_id, amount):
    amount = amount_value(amount)
    with get_connection() as conn:
        lock_user(conn, user_id)
        income = conn.execute("SELECT * FROM transactions WHERE id=? AND user_id=? AND kind='income' AND amount=?", (income_id, user_id, expected_amount)).fetchone()
        expense = conn.execute("SELECT * FROM transactions WHERE id=? AND user_id=? AND kind='expense' AND amount>0", (expense_id, user_id)).fetchone()
        if not income or not expense or income["income_source_id"] is not None:
            raise ValueError("Записи изменились или доход связан с источником: исправление отменено")
        if conn.execute("SELECT 1 FROM wallet_entries WHERE user_id=? AND (transaction_id IN (?,?) OR original_id=?)", (user_id, income_id, expense_id, expense_id)).fetchone():
            raise ValueError("Операции уже связаны с движением средств или возвратом")
        if amount > float(expense["amount"]):
            raise ValueError("Возврат больше покупки")
        user = conn.execute("SELECT financial_day FROM users WHERE user_id=?", (user_id,)).fetchone()
        key = financial_period_start_for_day(int(user["financial_day"]), datetime.fromisoformat(income["created_at"])).isoformat()
        changed = conn.execute("UPDATE months SET budget=budget-?,spent=spent-? WHERE user_id=? AND month=?", (expected_amount, amount, user_id, key))
        if changed.rowcount != 1:
            raise ValueError("Финансовый период не найден")
        conn.execute("UPDATE transactions SET kind='expense',amount=?,description=? WHERE user_id=? AND id=?", (-amount, expense["description"], user_id, income_id))
        conn.execute("INSERT INTO wallet_entries(transaction_id,user_id,operation,source,destination,original_id,original_data) VALUES (?,?,'refund','main','',?,?)", (income_id, user_id, expense_id, json.dumps(dict(income), ensure_ascii=False)))
