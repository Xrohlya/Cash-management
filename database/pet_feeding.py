"""Food is a cosmetic reward for a completed day, never a money transfer."""
from datetime import date, timedelta

from database.db import get_connection


def remember_daily_limit(user_id, limit, spent_today):
    with get_connection() as conn:
        conn.execute("INSERT INTO pet_daily_budget(user_id,day,allowance) VALUES (?,?,?) "
                     "ON CONFLICT(user_id,day) DO NOTHING",
                     (user_id, date.today().isoformat(), round(max(0, limit + spent_today), 2)))


def feeding_status(conn, user_id, today):
    yesterday = (date.fromisoformat(today) - timedelta(days=1)).isoformat()
    row = conn.execute("SELECT allowance FROM pet_daily_budget WHERE user_id=? AND day=?", (user_id, yesterday)).fetchone()
    if not row:
        return {"eligible": False, "title": "Кормление", "note": "Первый дневной итог появится завтра", "remaining": None}
    entries = conn.execute("SELECT kind,amount FROM transactions WHERE user_id=? AND created_at>=? AND created_at<?",
                           (user_id, yesterday + "T00:00:00", today + "T00:00:00")).fetchall()
    allowance = float(row["allowance"])
    spent = sum(float(item["amount"]) for item in entries if item["kind"] == "expense")
    remaining = round(max(0, allowance - spent), 2)
    saved = any(item["kind"] == "save" and float(item["amount"]) > 0 for item in entries)
    title = "Особое угощение" if remaining > 0 and saved else "Лакомство" if remaining >= allowance / 2 and remaining > 0 else "Порция корма"
    return {"eligible": remaining > 0, "remaining": remaining, "title": title if remaining > 0 else "Кормление",
            "note": f"Остаток лимита за {yesterday}: {remaining:g} ₽" if remaining > 0 else "Вчера свободного остатка не было. Можно просто поиграть."}
