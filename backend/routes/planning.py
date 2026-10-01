from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from backend.auth import current_user
from backend.notifications import schedule_telegram_refresh
from backend.planning_schemas import CategoryLimit, CategoryName, PlannedIncome, UndoOperation
from database.category_limits import delete_category_limit, save_category_limit
from database.planned_income import cancel_planned_income, confirm_planned_income, save_planned_income
from database.undo import undo_last_operation

router = APIRouter()


@router.post("/api/plans")
def add_plan(plan: PlannedIncome, user_id: int = Depends(current_user)):
    try:
        save_planned_income(user_id, plan.title, plan.amount, plan.due_date, plan.source_id)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    return {"ok": True}


@router.post("/api/plans/{plan_id}/edit")
def edit_plan(plan_id: int, plan: PlannedIncome, user_id: int = Depends(current_user)):
    try:
        save_planned_income(user_id, plan.title, plan.amount, plan.due_date, plan.source_id, plan_id)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    return {"ok": True}


@router.post("/api/plans/{plan_id}/cancel")
def cancel_plan(plan_id: int, user_id: int = Depends(current_user)):
    cancel_planned_income(user_id, plan_id)
    return {"ok": True}


@router.post("/api/plans/{plan_id}/confirm")
def confirm_plan(plan_id: int, background_tasks: BackgroundTasks, user_id: int = Depends(current_user)):
    try:
        created = confirm_planned_income(user_id, plan_id)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    if created:
        schedule_telegram_refresh(background_tasks, user_id)
    return {"ok": True, "created": created}


@router.post("/api/limits")
def save_limit(limit: CategoryLimit, user_id: int = Depends(current_user)):
    save_category_limit(user_id, limit.category, limit.amount)
    return {"ok": True}


@router.post("/api/limits/delete")
def remove_limit(limit: CategoryName, user_id: int = Depends(current_user)):
    delete_category_limit(user_id, limit.category)
    return {"ok": True}


@router.post("/api/operations/undo")
def undo_operation(data: UndoOperation, background_tasks: BackgroundTasks, user_id: int = Depends(current_user)):
    if not data.confirmed:
        raise HTTPException(400, "Подтвердите отмену операции")
    try:
        undo_last_operation(user_id, data.transaction_id)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    schedule_telegram_refresh(background_tasks, user_id)
    return {"ok": True}
