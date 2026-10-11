from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.auth import current_user
from backend.notifications import schedule_telegram_refresh
from backend.payloads import state
from database.wallets import spend, transfer, refund, refundable_expenses

router = APIRouter(prefix="/api/wallets")


class Amount(BaseModel):
    amount: float = Field(gt=0, le=1_000_000_000, allow_inf_nan=False)
    request_id: str = Field(min_length=8, max_length=100)


class Transfer(Amount):
    source: str = Field(max_length=32)
    destination: str = Field(max_length=32)


class Expense(Amount):
    wallet: str = Field(default="main", max_length=32)
    description: str = Field(default="Расход", max_length=255)


class Refund(Amount):
    original_id: int = Field(gt=0)


def apply(function, args, tasks, user_id):
    try:
        function(user_id, *args)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    schedule_telegram_refresh(tasks, user_id)
    return state(user_id)


@router.get("/refunds")
def candidates(user_id: int = Depends(current_user)):
    return refundable_expenses(user_id)


@router.post("/transfer")
def transfer_money(data: Transfer, background_tasks: BackgroundTasks, user_id: int = Depends(current_user)):
    return apply(transfer, (data.source, data.destination, data.amount, data.request_id), background_tasks, user_id)


@router.post("/expense")
def expense(data: Expense, background_tasks: BackgroundTasks, user_id: int = Depends(current_user)):
    return apply(spend, (data.wallet, data.amount, data.description, data.request_id), background_tasks, user_id)


@router.post("/refund")
def return_money(data: Refund, background_tasks: BackgroundTasks, user_id: int = Depends(current_user)):
    return apply(refund, (data.original_id, data.amount, data.request_id), background_tasks, user_id)
