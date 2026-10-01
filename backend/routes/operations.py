from fastapi import BackgroundTasks, Depends, HTTPException
from database.repository import add_expense, add_income, add_rent, add_to_savings, reset_user_data, update_expense
from backend.auth import current_user
from backend.notifications import schedule_telegram_refresh
from backend.payloads import state
from backend.schemas import ExpenseCorrection, Operation, ResetConfirmation
from fastapi import APIRouter

router = APIRouter()


@router.post("/api/transactions/{transaction_id}/edit")
def api_edit_expense(
    transaction_id: int,
    correction: ExpenseCorrection,
    background_tasks: BackgroundTasks,
    user_id: int = Depends(current_user),
):
    try:
        update_expense(user_id, transaction_id, correction.amount, correction.description)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    schedule_telegram_refresh(background_tasks, user_id)
    return state(user_id)


@router.post("/api/reset")
def api_reset(
    data: ResetConfirmation,
    background_tasks: BackgroundTasks,
    user_id: int = Depends(current_user),
):
    if data.confirmation != "УДАЛИТЬ ВСЕ":
        raise HTTPException(400, "Введите точную фразу: УДАЛИТЬ ВСЕ")
    reset_user_data(user_id)
    schedule_telegram_refresh(background_tasks, user_id)
    return state(user_id)


@router.post("/api/expense")
def api_expense(
    op: Operation,
    background_tasks: BackgroundTasks,
    user_id: int = Depends(current_user),
):
    if not add_expense(user_id, op.amount, op.description or "Расход", op.request_id):
        raise HTTPException(409, "Недостаточно средств в доступном бюджете.")
    schedule_telegram_refresh(background_tasks, user_id)
    return state(user_id)


@router.post("/api/income")
def api_income(
    op: Operation,
    background_tasks: BackgroundTasks,
    user_id: int = Depends(current_user),
):
    add_income(
        user_id,
        op.amount,
        0,
        op.description or "Доход",
        op.request_id,
    )
    schedule_telegram_refresh(background_tasks, user_id)
    return state(user_id)


@router.post("/api/rent")
def api_rent(
    op: Operation,
    background_tasks: BackgroundTasks,
    user_id: int = Depends(current_user),
):
    if not add_rent(user_id, op.amount, op.description or "Квартира", op.request_id):
        raise HTTPException(409, "Недостаточно средств в доступном бюджете.")
    schedule_telegram_refresh(background_tasks, user_id)
    return state(user_id)


@router.post("/api/save")
def api_save(
    op: Operation,
    background_tasks: BackgroundTasks,
    user_id: int = Depends(current_user),
):
    if not add_to_savings(user_id, op.amount, op.description or "Накопления", op.request_id):
        raise HTTPException(409, "Недостаточно средств в доступном бюджете.")
    schedule_telegram_refresh(background_tasks, user_id)
    return state(user_id)
