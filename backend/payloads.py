from datetime import timedelta
from database.repository import get_status_snapshot, get_user_profile
from services.analytics import current_period_stats


def state(user_id: int):
    snapshot = get_status_snapshot(user_id)
    profile = get_user_profile(user_id)
    end = snapshot["end"]
    goal = snapshot.get("goal")
    return {
        "available": round(snapshot["remaining"], 2),
        "today": round(snapshot["spent_today"], 2),
        "daily_limit": round(snapshot["daily_limit"], 2),
        "days_left": max(1, snapshot["days_left"]),
        "spent": round(snapshot["spent"], 2),
        "recurring": round(snapshot["recurring"], 2),
        "rent": round(snapshot["rent"], 2),
        "saved_this_month": round(snapshot["saved"], 2),
        "savings": round(snapshot["savings"], 2),
        "budget": round(snapshot["budget"], 2),
        "mandatory_percent": snapshot["mandatory_percent"],
        "financial_day": snapshot["financial_day"],
        "target_balance": round(snapshot["target_balance"], 2),
        "period_start": snapshot["start"].isoformat(),
        "period_end": (end - timedelta(days=1)).isoformat(),
        "profile": {
            "first_name": profile["first_name"] or "Пользователь",
            "username": profile["username"] or "",
        },
        "goal": (
            {
                "target": float(goal["target"]),
                "target_date": goal["target_date"],
                "current": round(snapshot["savings"], 2),
                "progress": min(100, round(snapshot["savings"] / float(goal["target"]) * 100, 1)),
            }
            if goal and float(goal["target"]) > 0
            else None
        ),
    }


def analytics_payload(user_id: int):
    stats = current_period_stats(user_id)
    return {
        "average": round(stats["avg"], 2),
        "forecast": round(stats["forecast"], 2),
        "categories": [
            {
                "name": name,
                "amount": round(amount, 2),
                "count": stats["category_counts"].get(name, 0),
            }
            for name, amount in sorted(
                stats["categories"].items(), key=lambda item: item[1], reverse=True
            )
        ],
        "daily": [
            {"date": day, "amount": round(amount, 2)}
            for day, amount in sorted(stats["daily"].items())
        ],
    }
