"""Assemble Telegram workflows, keeping unrestricted text handling last."""
from aiogram import F, Router
from aiogram.types import CallbackQuery
from bot.routes import budget, operations, reports, analytics, settings, messages
from bot.routes.common import answer_callback

router = Router()
router.message.filter(F.chat.type == "private")
router.callback_query.filter(F.message.chat.type == "private")


@router.callback_query.middleware()
async def acknowledge_callback(handler, event: CallbackQuery, data):
    await answer_callback(event)
    return await handler(event, data)


router.include_routers(
    budget.router, operations.router, reports.router,
    analytics.router, settings.router, messages.router,
)
