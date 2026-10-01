from collections import defaultdict
from datetime import date, timedelta

from database.db import get_connection
from services.categories import normalize_expense_category


def weekly_summary(user_id, today=None):
    today = today or date.today()
    start = today - timedelta(days=6)
    previous_start = start - timedelta(days=7)
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT created_at,kind,amount,description FROM transactions WHERE user_id=? "
            "AND created_at>=? AND created_at<?", (user_id, previous_start.isoformat(), (today + timedelta(days=1)).isoformat()),
        ).fetchall()
    totals = defaultdict(float)
    categories = defaultdict(float)
    previous_categories = defaultdict(float)
    previous_spent = 0.0
    for row in rows:
        current = row["created_at"][:10] >= start.isoformat()
        amount = float(row["amount"])
        if current:
            totals[row["kind"]] += amount
        if row["kind"] == "expense":
            category = normalize_expense_category(row["description"])
            if current:
                categories[category] += amount
            else:
                previous_spent += amount
                previous_categories[category] += amount
    change = round((totals["expense"] - previous_spent) / previous_spent * 100, 1) if previous_spent else None
    largest = max(categories, key=categories.get, default=None)
    insights = []
    if not totals["expense"]:
        insights.append("За последние 7 дней обычных расходов не было.")
    elif change is not None:
        insights.append(f"Обычные расходы {'снизились' if change < 0 else 'выросли' if change > 0 else 'не изменились'}" + (f" на {abs(change):g}%." if change else "."))
    else:
        insights.append("На прошлой неделе обычных расходов не было — сравнение в процентах недоступно.")
    if largest:
        insights.append(f"Больше всего потрачено в категории «{largest}».")
    growth = max(categories, key=lambda name: categories[name] - previous_categories[name], default=None)
    if growth and previous_categories[growth] and categories[growth] > previous_categories[growth]:
        insights.append(f"Расходы на «{growth}» увеличились относительно прошлых 7 дней.")
    return {"start": start.isoformat(), "end": today.isoformat(), "spent": round(totals["expense"], 2),
            "previous_spent": round(previous_spent, 2), "change_percent": change,
            "net_income": round(totals["income"] - totals["mandatory"], 2),
            "saved": round(totals["save"], 2), "payments": round(totals["recurring"] + totals["rent"], 2),
            "largest_category": largest, "insights": insights}
