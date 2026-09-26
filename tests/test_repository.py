import tempfile
import unittest
from pathlib import Path

import database.db as db
from database import repository
from services.analytics import current_period_stats, get_goal, set_goal


class RepositoryTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.original_path = db.SQLITE_PATH
        self.original_url = db.DATABASE_URL
        db.SQLITE_PATH = Path(self.tempdir.name) / "test.db"
        db.DATABASE_URL = ""
        db.init_db()

    def tearDown(self):
        db.SQLITE_PATH = self.original_path
        db.DATABASE_URL = self.original_url
        self.tempdir.cleanup()

    def test_users_have_isolated_balances_and_history(self):
        repository.add_income(101, 1000, 0)
        repository.add_income(202, 500, 0)
        self.assertTrue(repository.add_expense(101, 125, "Кафе"))

        self.assertEqual(float(repository.get_month(101)["spent"]), 125)
        self.assertEqual(float(repository.get_month(202)["spent"]), 0)
        self.assertEqual(len(repository.recent_transactions(101)), 3)
        self.assertEqual(len(repository.recent_transactions(202)), 2)

    def test_request_id_prevents_duplicate_operation(self):
        repository.add_income(101, 1000, 0)
        self.assertTrue(repository.add_expense(101, 100, "Еда", "request-0001"))
        self.assertTrue(repository.add_expense(101, 100, "Еда", "request-0001"))

        self.assertEqual(float(repository.get_month(101)["spent"]), 100)
        expenses = [row for row in repository.recent_transactions(101) if row["kind"] == "expense"]
        self.assertEqual(len(expenses), 1)

    def test_budget_cannot_go_below_zero(self):
        repository.add_income(101, 100, 0)
        self.assertFalse(repository.add_expense(101, 101, "Еда", "request-0002"))
        self.assertEqual(float(repository.get_month(101)["spent"]), 0)

    def test_expense_aliases_are_grouped_in_analytics(self):
        repository.add_income(303, 1000, 0)
        repository.add_expense(303, 100, "продукты")
        repository.add_expense(303, 150, "обед")
        repository.add_expense(303, 25, ". еда")
        repository.add_expense(303, 75, "Еда . еда")

        stats = current_period_stats(303)

        self.assertEqual(stats["categories"], {"Еда": 350.0})
        self.assertEqual(stats["category_counts"], {"Еда": 4})

    def test_subscription_and_generic_expense_aliases(self):
        self.assertEqual(repository.normalize_expense_category("- оплата Ai"), "Подписки")
        self.assertEqual(repository.normalize_expense_category("расход"), "Разное")

    def test_goals_are_stored_per_user(self):
        from datetime import date

        set_goal(101, 5000, date(2027, 1, 1))
        self.assertEqual(get_goal(101), (5000.0, date(2027, 1, 1)))
        self.assertIsNone(get_goal(202))

    def test_recurring_payment_runs_once_per_calendar_month(self):
        from datetime import date

        repository.add_income(101, 1000, 0)
        repository.add_recurring_payment(101, "Кофе", 120, "expense", 1)

        self.assertEqual(len(repository.apply_due_recurring_payments(101, date(2026, 9, 26))), 1)
        self.assertEqual(repository.apply_due_recurring_payments(101, date(2026, 9, 27)), [])
        self.assertEqual(float(repository.get_month(101)["spent"]), 120)
        expenses = [row for row in repository.recent_transactions(101) if row["kind"] == "expense"]
        self.assertEqual(len(expenses), 1)

    def test_smart_categories_cover_common_household_expenses(self):
        self.assertEqual(repository.normalize_expense_category("платёж по кредиту"), "Кредиты")
        self.assertEqual(repository.normalize_expense_category("домашний интернет"), "Дом и связь")

    def test_financial_day_is_per_user_and_rebuilds_current_summary(self):
        repository.add_income(101, 1000, 0)
        repository.add_expense(101, 125, "Кафе")

        repository.set_financial_day(101, 10)

        self.assertEqual(repository.get_financial_day(101), 10)
        self.assertEqual(repository.get_financial_day(202), 20)
        month = repository.get_month(101)
        self.assertEqual(float(month["budget"]), 1000)
        self.assertEqual(float(month["spent"]), 125)


if __name__ == "__main__":
    unittest.main()
