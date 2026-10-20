import tempfile
import unittest
from datetime import date
from pathlib import Path

from database import db, repository


class StartupPeriodTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path, self.url = db.SQLITE_PATH, db.DATABASE_URL
        db.SQLITE_PATH, db.DATABASE_URL = Path(self.temp.name) / "test.db", ""
        db.init_db()

    def tearDown(self):
        db.SQLITE_PATH, db.DATABASE_URL = self.path, self.url
        self.temp.cleanup()

    def test_startup_reads_all_users_without_creating_or_carrying_months(self):
        repository.ensure_user(101, "Test", "owner")
        repository.ensure_user(202, "Other", "other")
        with db.get_connection() as conn:
            conn.execute("UPDATE users SET savings=160000 WHERE user_id=101")
            conn.execute("UPDATE users SET financial_day=8 WHERE user_id=202")
            conn.execute("INSERT INTO months(user_id,month,budget,spent,rent,saved) VALUES (101,'2026-09-20',200000,10000,50000,90000)")
            conn.execute("INSERT INTO months(user_id,month,budget) VALUES (202,'2026-10-08',1000)")
        users = repository.list_user_summaries(today=date(2026, 10, 20))
        self.assertEqual(users[0]["balance"], 0)
        self.assertEqual(users[0]["previous_balance"], 50000)
        self.assertEqual(users[0]["savings"], 160000)
        self.assertEqual(users[0]["period_start"], "2026-10-20")
        self.assertEqual(users[1]["balance"], 1000)
        with db.get_connection() as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) n FROM months").fetchone()["n"], 2)

    def test_first_snapshot_in_new_month_keeps_prior_history(self):
        repository.ensure_user(101)
        snapshot = repository.get_status_snapshot(101, today=date(2026, 10, 20))
        self.assertEqual(snapshot["remaining"], 0)
        self.assertEqual(snapshot["start"], date(2026, 10, 20))
