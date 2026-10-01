from fastapi import BackgroundTasks, Depends, HTTPException
from database.repository import create_income_source, delete_income_source, list_income_sources, update_income_source
from backend.auth import current_user
from backend.notifications import schedule_telegram_refresh
from backend.schemas import IncomeSource
from fastapi import APIRouter

router = APIRouter()


@router.get("/api/income-sources")
def api_income_sources(user_id: int = Depends(current_user)):
    return [dict(row) for row in list_income_sources(user_id)]


@router.post("/api/income-sources")
def api_add_income_source(
    source: IncomeSource,
    background_tasks: BackgroundTasks,
    user_id: int = Depends(current_user),
):
    try:
        create_income_source(user_id, source.name, source.withholding_percent)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    schedule_telegram_refresh(background_tasks, user_id)
    return [dict(row) for row in list_income_sources(user_id)]


@router.post("/api/income-sources/{source_id}")
def api_update_income_source(
    source_id: int,
    source: IncomeSource,
    background_tasks: BackgroundTasks,
    user_id: int = Depends(current_user),
):
    try:
        update_income_source(user_id, source_id, source.name, source.withholding_percent)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    schedule_telegram_refresh(background_tasks, user_id)
    return [dict(row) for row in list_income_sources(user_id)]


@router.post("/api/income-sources/{source_id}/delete")
def api_delete_income_source(
    source_id: int,
    background_tasks: BackgroundTasks,
    user_id: int = Depends(current_user),
):
    delete_income_source(user_id, source_id)
    schedule_telegram_refresh(background_tasks, user_id)
    return [dict(row) for row in list_income_sources(user_id)]
