import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from pathlib import Path

from database import db, repository
from database.openings import rollover_all_users
from database.periods import financial_period_start_for_day, financial_period_end_for_start, ensure_month, rebuild_month_from_transactions
from services.analytics import current_period_stats


class OpeningBalanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path, self.url = db.SQLITE_PATH, db.DATABASE_URL
        db.SQLITE_PATH, db.DATABASE_URL = Path(self.temp.name) / "test.db", ""
        db.init_db()
        repository.ensure_user(101)
        self.start = financial_period_start_for_day(20)
        self.previous = financial_period_start_for_day(20, self.start - timedelta(days=1))
        with db.get_connection() as conn:
            conn.execute("INSERT INTO months(user_id,month,budget,spent,rent,saved) VALUES (?,?,395099.86,131658,52355,90000)", (101, self.previous.isoformat()))
            conn.execute("UPDATE users SET savings=160000 WHERE user_id=101")

    def tearDown(self):
        db.SQLITE_PATH, db.DATABASE_URL = self.path, self.url
        self.temp.cleanup()

    def test_existing_empty_period_receives_opening_once_without_income(self):
        with db.get_connection() as conn:
            conn.execute("INSERT INTO months(user_id,month) VALUES (?,?)", (101, self.start.isoformat()))
        for _ in range(3):
            rollover_all_users()
        snapshot = repository.get_status_snapshot(101)
        self.assertAlmostEqual(snapshot["remaining"], 121086.86)
        self.assertAlmostEqual(snapshot["opening_balance"], 121086.86)
        self.assertEqual(snapshot["savings"], 160000)
        self.assertEqual(current_period_stats(101)["income"], 0)
        with db.get_connection() as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) n FROM transactions").fetchone()["n"], 0)
            self.assertEqual(conn.execute("SELECT COUNT(*) n FROM period_openings").fetchone()["n"], 1)
            old = conn.execute("SELECT * FROM months WHERE user_id=101 AND month=?", (self.previous.isoformat(),)).fetchone()
            self.assertEqual(old["budget"], 395099.86)

    def test_concurrent_initialisation_is_idempotent(self):
        with ThreadPoolExecutor(max_workers=4) as executor:
            list(executor.map(lambda _: ensure_month(101), range(8)))
        self.assertAlmostEqual(repository.get_status_snapshot(101)["remaining"], 121086.86)

    def test_new_income_expense_refund_and_rebuild_keep_opening(self):
        repository.add_income(101, 1000, 0)
        repository.add_expense(101, 500, "Еда")
        from database.wallets import refund
        expense = repository.recent_transactions(101)[0]
        refund(101, expense["id"], 200, "refund-opening-test")
        rebuild_month_from_transactions(101, self.start)
        state = repository.get_status_snapshot(101)
        self.assertAlmostEqual(state["remaining"], 121786.86)
        self.assertEqual(current_period_stats(101)["income"], 1000)

    def test_mini_app_separates_opening_from_net_income(self):
        from backend.payloads import state
        repository.create_income_source(101, "Кафе", 6)
        source = repository.list_income_sources(101)[0]
        repository.add_income_from_source(101, 1000, source["id"])
        payload = state(101)
        self.assertEqual(payload["budget"], 940)
        self.assertAlmostEqual(payload["opening_balance"], 121086.86)
        self.assertAlmostEqual(payload["available"], 122026.86)
        self.assertEqual(repository.list_income_sources(101)[0]["withheld_total"], 60)

    def test_next_period_carries_remaining_not_original_opening(self):
        repository.add_income(101, 1000, 0)
        repository.add_expense(101, 500, "Еда")
        next_start = financial_period_end_for_start(self.start)
        ensure_month(101, next_start.isoformat(), today=next_start)
        with db.get_connection() as conn:
            row = conn.execute("SELECT budget FROM months WHERE user_id=101 AND month=?", (next_start.isoformat(),)).fetchone()
        self.assertAlmostEqual(row["budget"], 121586.86)

    def test_period_change_preserves_funds_and_repeat_does_not_duplicate(self):
        repository.add_income(101, 1000, 0)
        before = repository.get_status_snapshot(101)["remaining"]
        repository.set_financial_day(101, 8)
        self.assertAlmostEqual(repository.get_status_snapshot(101)["remaining"], before)
        repository.set_financial_day(101, 20)
        self.assertAlmostEqual(repository.get_status_snapshot(101)["remaining"], before)
        repository.set_financial_day(101, 20)
        self.assertAlmostEqual(repository.get_status_snapshot(101)["remaining"], before)

    def test_different_users_and_full_reset_are_isolated(self):
        repository.ensure_user(202)
        rollover_all_users()
        self.assertEqual(repository.get_status_snapshot(202)["remaining"], 0)
        repository.reset_user_data(101)
        self.assertEqual(repository.get_status_snapshot(101)["remaining"], 0)
        self.assertEqual(repository.get_status_snapshot(202)["remaining"], 0)

    def test_closed_period_cannot_be_changed_after_transfer(self):
        ensure_month(101)
        with self.assertRaisesRegex(ValueError, "закрыт"):
            rebuild_month_from_transactions(101, self.previous)
        from datetime import datetime
        with self.assertRaisesRegex(ValueError, "закрыт"):
            repository.add_expense(101, 100, "Еда", created_at=datetime.combine(self.previous, datetime.min.time()))

    def test_missing_intermediate_month_and_negative_balance_are_preserved(self):
        with db.get_connection() as conn:
            conn.execute("UPDATE months SET budget=0,spent=100,rent=0,saved=0 WHERE user_id=101")
        distant = financial_period_end_for_start(financial_period_end_for_start(self.start))
        ensure_month(101, distant.isoformat(), today=distant)
        with db.get_connection() as conn:
            row = conn.execute("SELECT budget FROM months WHERE user_id=101 AND month=?", (distant.isoformat(),)).fetchone()
        self.assertEqual(row["budget"], -100)

    def test_overlapping_legacy_period_is_not_carried_twice(self):
        repository.ensure_user(202)
        with db.get_connection() as conn:
            conn.execute("UPDATE users SET financial_day=8 WHERE user_id=202")
            conn.execute("INSERT INTO months(user_id,month,budget) VALUES (202,?,235000)", (self.previous.isoformat(),))
        ensure_month(202)
        self.assertEqual(repository.get_status_snapshot(202)["remaining"], 0)
