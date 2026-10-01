from datetime import date

from database.category_limits import list_category_limits
from database.planned_income import list_planned_income
from database.undo import recent_undos, undo_candidate
from services.categories import CATEGORY_ALIASES
from services.weekly_summary import weekly_summary


def planning_payload(user_id, state, radar, analytics):
    plans = list_planned_income(user_id)
    today = date.today().isoformat()
    expected = sum(item["net"] for item in plans if item["source_available"] and today <= item["due_date"] <= state["period_end"])
    spent = {item["name"]: item["amount"] for item in analytics["categories"]}
    limits = []
    for item in list_category_limits(user_id):
        amount = float(item["amount"])
        actual = float(spent.get(item["category"], 0))
        progress = round(actual / amount * 100, 1)
        limits.append({**item, "spent": actual, "remaining": round(max(0, amount - actual), 2),
                       "progress": progress, "status": "red" if progress >= 100 else "yellow" if progress >= 80 else "green"})
    candidate = undo_candidate(user_id)
    if candidate and candidate.get("allowed") and not state["period_start"] <= candidate["created_at"][:10] <= state["period_end"]:
        candidate["allowed"] = False
        candidate["reason"] = "Последняя операция относится к прошлому периоду"
    return {"plans": plans, "expected_total": round(expected, 2),
            "projected_with_income": round(radar["projected_balance"] + expected, 2),
            "limits": limits, "weekly": weekly_summary(user_id), "undo": candidate,
            "undo_history": recent_undos(user_id), "categories": sorted(set(CATEGORY_ALIASES.values()))}
