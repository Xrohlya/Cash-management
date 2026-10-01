from fastapi import BackgroundTasks, Depends, HTTPException
from database.repository import create_extra_account, delete_extra_account, list_extra_accounts, transfer_extra_account
from backend.auth import current_user
from backend.notifications import schedule_telegram_refresh
from backend.payloads import state
from backend.schemas import AccountTransfer, ExtraAccount
from fastapi import APIRouter

router = APIRouter()


@router.get("/api/accounts")
def api_accounts(user_id: int = Depends(current_user)):
    return [dict(row) for row in list_extra_accounts(user_id)]


@router.post("/api/accounts")
def api_add_account(account: ExtraAccount, user_id: int = Depends(current_user)):
    try:
        create_extra_account(user_id, account.name)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    return [dict(row) for row in list_extra_accounts(user_id)]


@router.post("/api/accounts/{account_id}/delete")
def api_delete_account(account_id: int, user_id: int = Depends(current_user)):
    try:
        delete_extra_account(user_id, account_id)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    return [dict(row) for row in list_extra_accounts(user_id)]


@router.post("/api/accounts/{account_id}/transfer")
def api_transfer_account(
    account_id: int,
    transfer: AccountTransfer,
    background_tasks: BackgroundTasks,
    user_id: int = Depends(current_user),
):
    try:
        transfer_extra_account(
            user_id, account_id, transfer.amount, transfer.direction, transfer.request_id
        )
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    schedule_telegram_refresh(background_tasks, user_id)
    return {
        "state": state(user_id),
        "accounts": [dict(row) for row in list_extra_accounts(user_id)],
    }
