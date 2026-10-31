import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from aiogram.exceptions import TelegramNetworkError, TelegramRetryAfter
from aiogram.methods import EditMessageText
from backend.sync_worker import process_refresh
from database import db
from database.telegram_sync import enqueue, claim, finish
from database.operations import add_income, add_expense


class SyncQueueTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path, self.url = db.SQLITE_PATH, db.DATABASE_URL
        db.SQLITE_PATH, db.DATABASE_URL = Path(self.temp.name) / "test.db", ""
        db.init_db()

    def tearDown(self):
        db.SQLITE_PATH, db.DATABASE_URL = self.path, self.url
        self.temp.cleanup()

    def test_newer_revision_survives_acknowledgement_and_users_are_isolated(self):
        enqueue(101)
        enqueue(202)
        job = claim(101, now=10)
        self.assertIsNone(claim(101, now=10))
        enqueue(101)
        finish(job, now=11)
        newer = claim(101, now=11)
        self.assertEqual(newer["revision"], 2)
        finish(newer, now=11)
        self.assertIsNone(claim(101, now=11))
        self.assertEqual(claim(now=11)["user_id"], 202)

    def test_crashed_worker_lease_expires_and_old_ack_cannot_delete_new_claim(self):
        enqueue(101)
        old = claim(now=10)
        self.assertIsNone(claim(now=309))
        recovered = claim(now=310)
        finish(old, now=311)
        self.assertIsNone(claim(now=311))
        finish(recovered, now=312)
        self.assertIsNone(claim(now=1000))

    def test_financial_operation_commits_with_queue_and_duplicate_does_not_reapply(self):
        add_income(101, 1000, 0, request_id="income")
        first = claim(101, now=10)
        finish(first, now=10)
        add_expense(101, 100, "Еда", request_id="expense")
        second = claim(101, now=10)
        finish(second, now=10)
        add_expense(101, 100, "Еда", request_id="expense")
        self.assertIsNone(claim(101, now=1000))
        with db.get_connection() as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) n FROM transactions").fetchone()["n"], 2)

    def test_failed_queue_write_rolls_back_the_financial_operation(self):
        with patch("database.operations.mark_dirty", side_effect=RuntimeError("Queue unavailable")):
            with self.assertRaises(RuntimeError):
                add_income(101, 1000, 0, request_id="income")
        with db.get_connection() as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) n FROM transactions").fetchone()["n"], 0)
            self.assertEqual(conn.execute("SELECT budget FROM months WHERE user_id=101").fetchone()["budget"], 0)
            self.assertEqual(conn.execute("SELECT COUNT(*) n FROM operation_requests").fetchone()["n"], 0)

    async def test_network_failure_is_persisted_and_retried_without_new_operation(self):
        enqueue(101)
        method = EditMessageText(chat_id=101, message_id=5, text="Test")
        with patch("backend.notifications.refresh_telegram_status", new_callable=AsyncMock) as send:
            send.side_effect = TelegramNetworkError(method, "Disconnected")
            with patch("database.telegram_sync.time.time", return_value=100):
                await process_refresh(101)
            self.assertIsNone(claim(now=104))
            send.side_effect = None
            send.return_value = True
            with patch("database.telegram_sync.time.time", return_value=105):
                await process_refresh(101)
            self.assertEqual(send.await_count, 2)
            self.assertIsNone(claim(now=1000))

    async def test_rate_limit_respects_telegram_delay(self):
        enqueue(101)
        method = EditMessageText(chat_id=101, message_id=5, text="Test")
        with patch("backend.notifications.refresh_telegram_status", new_callable=AsyncMock,
                   side_effect=TelegramRetryAfter(method, "Flood", retry_after=60)):
            with patch("database.telegram_sync.time.time", return_value=100):
                await process_refresh(101)
        self.assertIsNone(claim(now=160))
        self.assertEqual(claim(now=161)["attempts"], 1)
