from fastapi import BackgroundTasks, Depends
from database.repository import set_financial_day, set_target_balance
from services.analytics import clear_goal, set_goal
from backend.auth import current_user
from backend.notifications import schedule_telegram_refresh
from backend.payloads import state
from backend.schemas import GoalSettings, PeriodSettings, RadarSettings
from fastapi import APIRouter

router = APIRouter()


@router.post("/api/goal")
def api_set_goal(
    goal: GoalSettings,
    background_tasks: BackgroundTasks,
    user_id: int = Depends(current_user),
):
    set_goal(user_id, goal.target, goal.target_date)
    schedule_telegram_refresh(background_tasks, user_id)
    return state(user_id)


@router.post("/api/goal/clear")
def api_clear_goal(
    background_tasks: BackgroundTasks,
    user_id: int = Depends(current_user),
):
    clear_goal(user_id)
    schedule_telegram_refresh(background_tasks, user_id)
    return state(user_id)


@router.post("/api/settings/period")
def api_set_period(
    settings_data: PeriodSettings,
    background_tasks: BackgroundTasks,
    user_id: int = Depends(current_user),
):
    set_financial_day(user_id, settings_data.financial_day)
    schedule_telegram_refresh(background_tasks, user_id)
    return state(user_id)


@router.post("/api/settings/radar")
def api_set_radar(
    settings_data: RadarSettings,
    background_tasks: BackgroundTasks,
    user_id: int = Depends(current_user),
):
    set_target_balance(user_id, settings_data.target_balance)
    schedule_telegram_refresh(background_tasks, user_id)
    return state(user_id)
