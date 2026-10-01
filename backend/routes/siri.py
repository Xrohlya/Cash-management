import uuid
from datetime import datetime
from fastapi import BackgroundTasks, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from database.repository import add_expense, get_status_snapshot
from services.parser import extract_date, parse_expense, strip_date_words
from backend.auth import siri_user
from backend.notifications import schedule_telegram_refresh
from backend.schemas import SiriExpense
from fastapi import APIRouter

router = APIRouter()


@router.post("/api/siri/expense", response_class=PlainTextResponse)
def api_siri_expense(
    op: SiriExpense,
    background_tasks: BackgroundTasks,
    user_id: int = Depends(siri_user),
):
    query = op.text.casefold().strip()
    snapshot = get_status_snapshot(user_id)
    if "остат" in query:
        return (
            f"Осталось {snapshot['remaining']:.0f} рублей. "
            f"Лимит на день {snapshot['daily_limit']:.0f} рублей."
        )
    if "сегодня" in query and ("потрат" in query or "расход" in query):
        return f"Сегодня потрачено {snapshot['spent_today']:.0f} рублей."
    if "потрат" in query or "расходы за месяц" in query:
        return f"За текущий период потрачено {snapshot['spent']:.0f} рублей."

    amount, description = parse_expense(strip_date_words(op.text))
    if amount is None or amount <= 0:
        raise HTTPException(422, "Назовите сумму цифрами, например: 500 рублей еда.")

    expense_date = extract_date(op.text)
    created_at = None
    if expense_date:
        created_at = datetime.combine(expense_date, datetime.min.time()).replace(hour=12)

    request_id = f"siri-{uuid.uuid4().hex}"
    if not add_expense(user_id, amount, description, request_id, created_at):
        raise HTTPException(409, "Недостаточно средств в доступном бюджете.")

    snapshot = get_status_snapshot(user_id)
    schedule_telegram_refresh(background_tasks, user_id)
    return (
        f"Записано: {amount:g} рублей, {description}. "
        f"Осталось {snapshot['remaining']:.0f} рублей."
    )
