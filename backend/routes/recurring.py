from fastapi import BackgroundTasks, Depends
from database.repository import add_recurring_payment, apply_due_recurring_payments, delete_recurring_payment, list_recurring_payments
from backend.auth import current_user
from backend.notifications import schedule_telegram_refresh
from backend.schemas import RecurringPayment
from fastapi import APIRouter

router = APIRouter()


@router.get("/api/recurring")
def api_recurring(user_id: int = Depends(current_user)):
    apply_due_recurring_payments(user_id)
    return [dict(row) for row in list_recurring_payments(user_id)]


@router.post("/api/recurring")
def api_add_recurring(
    payment: RecurringPayment,
    background_tasks: BackgroundTasks,
    user_id: int = Depends(current_user),
):
    add_recurring_payment(
        user_id,
        payment.title,
        payment.amount,
        payment.kind,
        payment.day_of_month,
    )
    schedule_telegram_refresh(background_tasks, user_id)
    return [dict(row) for row in list_recurring_payments(user_id)]


@router.post("/api/recurring/{payment_id}/delete")
def api_delete_recurring(
    payment_id: int,
    background_tasks: BackgroundTasks,
    user_id: int = Depends(current_user),
):
    delete_recurring_payment(user_id, payment_id)
    schedule_telegram_refresh(background_tasks, user_id)
    return [dict(row) for row in list_recurring_payments(user_id)]
