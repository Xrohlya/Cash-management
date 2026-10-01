from datetime import date, timedelta
from fastapi import Depends, Query
from database.repository import list_recurring_payments, list_income_sources, list_extra_accounts, recent_transactions
from services.analytics import financial_radar
from backend.auth import current_user
from backend.payloads import analytics_payload, state
from fastapi import APIRouter

router = APIRouter()


@router.get("/api/state")
def api_state(user_id: int = Depends(current_user)):
    return state(user_id)


@router.get("/api/dashboard")
def api_dashboard(user_id: int = Depends(current_user)):
    current_state = state(user_id)
    recurring = [dict(row) for row in list_recurring_payments(user_id)]
    return {
        "state": current_state,
        "transactions": [dict(row) for row in recent_transactions(user_id, 30)],
        "analytics": analytics_payload(user_id),
        "radar": financial_radar(
            user_id,
            current_state["available"],
            recurring,
            target_balance=current_state["target_balance"],
            period=(
                date.fromisoformat(current_state["period_start"]),
                date.fromisoformat(current_state["period_end"]) + timedelta(days=1),
            ),
        ),
        "recurring": recurring,
        "income_sources": [dict(row) for row in list_income_sources(user_id)],
        "accounts": [dict(row) for row in list_extra_accounts(user_id)],
    }


@router.get("/api/transactions")
def api_transactions(
    limit: int = Query(default=30, ge=1, le=100),
    user_id: int = Depends(current_user),
):
    return [dict(row) for row in recent_transactions(user_id, limit)]


@router.get("/api/analytics")
def api_analytics(user_id: int = Depends(current_user)):
    return analytics_payload(user_id)
