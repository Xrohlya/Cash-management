import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from aiogram import Bot
from aiogram.dispatcher.event.bases import UNHANDLED
from aiogram.types import Message
from fastapi.testclient import TestClient

from backend.auth import current_user
from backend.main import app
from bot.handlers import router
from database import db, repository


class ApiRoutesTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.original_path, self.original_url = db.SQLITE_PATH, db.DATABASE_URL
        db.SQLITE_PATH = Path(self.tempdir.name) / "test.db"
        db.DATABASE_URL = ""
        db.init_db()
        self.user_id = 101
        app.dependency_overrides[current_user] = lambda: self.user_id
        self.refresh = patch("backend.notifications.refresh_telegram_status", new_callable=AsyncMock)
        self.refresh_mock = self.refresh.start()
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        self.refresh.stop()
        app.dependency_overrides.clear()
        db.SQLITE_PATH, db.DATABASE_URL = self.original_path, self.original_url
        self.tempdir.cleanup()

    def test_operation_updates_dashboard_and_schedules_telegram_refresh(self):
        for path, amount in (("income", 1000), ("expense", 125)):
            response = self.client.post(f"/api/{path}", json={
                "amount": amount, "description": "Food", "request_id": f"request-{path}",
            })
            self.assertEqual(response.status_code, 200, response.text)
        response = self.client.get("/api/dashboard")
        self.assertEqual(response.status_code, 200, response.text)
        dashboard = response.json()
        self.assertEqual(dashboard["state"]["available"], 875)
        self.assertEqual(len(dashboard["transactions"]), 2)
        self.assertEqual(self.refresh_mock.await_count, 2)
        self.refresh_mock.assert_awaited_with(101)
        self.user_id = 202
        other = self.client.get("/api/dashboard").json()
        self.assertEqual(other["state"]["available"], 0)
        self.assertEqual(other["transactions"], [])

    def test_account_transfer_keeps_expenses_separate(self):
        repository.add_income(101, 1000, 0)
        response = self.client.post("/api/accounts", json={"name": "Reserve"})
        self.assertEqual(response.status_code, 200, response.text)
        account_id = response.json()[0]["id"]
        response = self.client.post(f"/api/accounts/{account_id}/transfer", json={
            "amount": 300, "direction": "to_account", "request_id": "transfer-test",
        })
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["state"]["available"], 700)
        self.assertEqual(response.json()["state"]["spent"], 0)
        self.assertEqual(response.json()["accounts"][0]["balance"], 300)

    def test_unauthenticated_request_and_unconfirmed_reset_are_rejected(self):
        app.dependency_overrides.clear()
        self.assertEqual(self.client.get("/api/dashboard").status_code, 401)
        app.dependency_overrides[current_user] = lambda: self.user_id
        repository.add_income(101, 1000, 0)
        self.assertEqual(self.client.post("/api/reset", json={"confirmation": "no"}).status_code, 400)
        self.assertEqual(repository.get_status_snapshot(101)["remaining"], 1000)


class TelegramRoutesTest(unittest.IsolatedAsyncioTestCase):
    async def test_start_is_routed_once_and_group_chats_are_excluded(self):
        bot = Bot("123456:test-token")
        message = Message.model_validate({
            "message_id": 1, "date": 0,
            "chat": {"id": 101, "type": "private"},
            "from": {"id": 101, "is_bot": False, "first_name": "Test"},
            "text": "/start", "entities": [{"type": "bot_command", "offset": 0, "length": 6}],
        }).as_(bot)
        try:
            with patch("bot.routes.budget.ensure_user"), patch("bot.routes.budget.delete_user_message", new_callable=AsyncMock), patch("bot.routes.budget.update_status", new_callable=AsyncMock) as update:
                await router.propagate_event("message", message, bot=bot)
                update.assert_awaited_once_with(message, 101)
                group = message.model_copy(update={"chat": message.chat.model_copy(update={"type": "group"})})
                self.assertIs(await router.propagate_event("message", group, bot=bot), UNHANDLED)
                self.assertEqual(update.await_count, 1)
        finally:
            await bot.session.close()

    def test_fallback_is_last_and_all_workflows_are_registered(self):
        self.assertEqual(router.sub_routers[-1].message.handlers[-1].callback.__name__, "plain_text")
        self.assertEqual(sum(len(child.message.handlers) for child in router.sub_routers), 19)
        self.assertEqual(sum(len(child.callback_query.handlers) for child in router.sub_routers), 17)
