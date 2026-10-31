from datetime import date
import json
from pathlib import Path
import tempfile
import unittest

from database import db, repository
from database.audit import audit_balances
from database.wallets import transfer, spend, refund
from tools.backup_postgres import TABLES
from tools.verify_backup import verify_backup


class BalanceAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path, self.url = db.SQLITE_PATH, db.DATABASE_URL
        db.SQLITE_PATH, db.DATABASE_URL = Path(self.temp.name) / "test.db", ""
        db.init_db()

    def tearDown(self):
        db.SQLITE_PATH, db.DATABASE_URL = self.path, self.url
        self.temp.cleanup()

    def seed(self):
        repository.add_income(101, 10000, 0)
        repository.add_to_savings(101, 1000)
        repository.add_expense(101, 250, "Еда")
        repository.create_extra_account(101, "Отпуск")
        account_id = repository.list_extra_accounts(101)[0]["id"]
        transfer(101, "main", f"account:{account_id}", 500, "move")
        spend(101, f"account:{account_id}", 100, "Еда", "spend")
        with db.get_connection() as conn:
            original = conn.execute("SELECT id FROM transactions WHERE kind='wallet_expense'").fetchone()["id"]
        refund(101, original, 25, "return")

    def test_reconciliation_is_read_only_and_detects_only_the_changed_user(self):
        self.seed()
        repository.add_income(202, 500, 0)
        result = audit_balances()
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["checked"], 9)
        with db.get_connection() as conn:
            conn.execute("UPDATE months SET spent=spent+10 WHERE user_id=101")
        result = audit_balances()
        self.assertEqual(len(result["findings"]), 1)
        self.assertEqual(result["findings"][0]["user_id"], 101)
        self.assertEqual(result["findings"][0]["difference"], "10.00")
        self.assertEqual(audit_balances(), result)

    def test_backup_roundtrip_leaves_live_sqlite_untouched(self):
        self.seed()
        with db.get_connection() as conn:
            tables = {table: [dict(row) for row in conn.execute(f"SELECT {cols} FROM {table}").fetchall()]
                      for table, cols in TABLES.items()}
        path = Path(self.temp.name) / "backup.json"
        path.write_text(json.dumps({"tables": tables}), encoding="utf-8")
        result = verify_backup(path)
        self.assertEqual(result["audit"]["findings"], [])
        self.assertEqual(result["missing_tables"], [])
        self.assertEqual(db.SQLITE_PATH, Path(self.temp.name) / "test.db")
        self.assertEqual(audit_balances()["findings"], [])

    def test_backup_with_unknown_table_is_rejected(self):
        path = Path(self.temp.name) / "bad.json"
        path.write_text(json.dumps({"tables": {"users": [], "months": [], "transactions": [],
                                                "unexpected": []}}), encoding="utf-8")
        with self.assertRaises(ValueError):
            verify_backup(path, date(2026, 10, 31))
