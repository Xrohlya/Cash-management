import unittest
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor

from tests import test_pets as fixtures
from database import db, repository
from database.wallets import spend, transfer, refund, refundable_expenses
from database.wallet_corrections import correct_income_as_refund
from services.wallet_commands import parse_wallet_command


class WalletTests(unittest.TestCase):
    setUp = fixtures.PetWorldTests.setUp
    tearDown = fixtures.PetWorldTests.tearDown

    def seed(self):
        repository.add_income(101, 10000, 0)
        repository.add_to_savings(101, 3000)
        repository.create_extra_account(101, "Отпуск")
        return f"account:{repository.list_extra_accounts(101)[0]['id']}"

    def test_transfer_spend_and_refund_do_not_change_main_or_income(self):
        wallet = self.seed()
        transfer(101, "savings", wallet, 1000, "transfer-one")
        spend(101, wallet, 500, "Такси", "expense-one")
        original = refundable_expenses(101)[0]
        refund(101, original["id"], 200, "refund-one")
        state = repository.get_status_snapshot(101)
        self.assertEqual((state["budget"], state["remaining"], state["savings"]), (10000, 7000, 2000))
        self.assertEqual(repository.list_extra_accounts(101)[0]["balance"], 700)
        transfer(101, wallet, "main", 700, "transfer-back")
        self.assertEqual(repository.get_status_snapshot(101)["remaining"], 7700)
        repository.rebuild_month_from_transactions(101, repository.financial_period_start(101))
        self.assertEqual(repository.get_status_snapshot(101)["remaining"], 7700)

    def test_main_refund_is_not_income_and_can_be_partial(self):
        self.seed()
        spend(101, "main", 1000, "Разное", "expense-one")
        original = refundable_expenses(101)[0]
        refund(101, original["id"], 400, "refund-one")
        refund(101, original["id"], 400, "refund-one")
        self.assertEqual(repository.get_status_snapshot(101)["remaining"], 6400)
        with self.assertRaises(ValueError):
            refund(101, original["id"], 601, "refund-two")
        self.assertEqual(refundable_expenses(101)[0]["refundable"], 600)
        with self.assertRaises(ValueError):
            refund(202, original["id"], 10, "other-user")

    def test_concurrent_refunds_never_exceed_purchase(self):
        self.seed()
        spend(101, "main", 100, "Разное", "expense-one")
        original = refundable_expenses(101)[0]
        def attempt(index):
            try:
                refund(101, original["id"], 60, f"refund-{index}")
                return True
            except ValueError:
                return False
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sum(pool.map(attempt, range(2))), 1)

    def test_insufficient_transfer_rolls_back_and_idempotency(self):
        wallet = self.seed()
        with self.assertRaises(ValueError):
            transfer(101, "savings", wallet, 4000, "transfer-one")
        transfer(101, "savings", wallet, 1000, "transfer-one")
        transfer(101, "savings", wallet, 1000, "transfer-one")
        self.assertEqual(repository.get_savings(101), 2000)

    def test_audited_income_correction_adds_only_difference_to_balance(self):
        self.seed()
        repository.add_expense(101, 2850, "Разное")
        expense = refundable_expenses(101)[0]
        repository.add_income(101, 2800, 0)
        income_id = repository.recent_transactions(101)[0]["id"]
        before = repository.get_status_snapshot(101)
        correct_income_as_refund(101, income_id, 2800, expense["id"], 2850)
        after = repository.get_status_snapshot(101)
        self.assertEqual(after["remaining"], before["remaining"] + 50)
        self.assertEqual(after["budget"], before["budget"] - 2800)
        self.assertEqual(refundable_expenses(101), [])
        with db.get_connection() as conn:
            self.assertIsNotNone(conn.execute("SELECT original_data FROM wallet_entries WHERE transaction_id=?", (income_id,)).fetchone()["original_data"])

    def test_commands_and_api(self):
        wallet = self.seed()
        accounts = repository.list_extra_accounts(101)
        self.assertEqual(parse_wallet_command("расход 500 со счета Отпуск такси", accounts), ("expense", 500, (wallet, "такси")))
        self.assertEqual(parse_wallet_command("перевод 500 из накоплений на счет Отпуск", accounts), ("transfer", 500, ("savings", wallet)))
        with patch("backend.routes.wallets.schedule_telegram_refresh"):
            response = self.client.post("/api/wallets/expense", json={"wallet": "savings", "amount": 500, "description": "Разное", "request_id": "expense-one"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["available"], 7000)
        self.assertEqual(repository.get_savings(101), 2500)

    def test_main_edit_and_undo_remain_available_until_refund(self):
        from database.undo import undo_last_operation, undo_candidate
        self.seed()
        spend(101, "main", 500, "Разное", "expense-one")
        original = refundable_expenses(101)[0]
        repository.update_expense(101, original["id"], 600, "Разное")
        self.assertEqual(repository.get_status_snapshot(101)["remaining"], 6400)
        self.assertTrue(undo_candidate(101)["allowed"])
        undo_last_operation(101, original["id"])
        self.assertEqual(repository.get_status_snapshot(101)["remaining"], 7000)
        spend(101, "main", 500, "Разное", "expense-two")
        original = refundable_expenses(101)[0]
        refund(101, original["id"], 100, "refund-one")
        with self.assertRaises(ValueError):
            repository.update_expense(101, original["id"], 600, "Разное")
