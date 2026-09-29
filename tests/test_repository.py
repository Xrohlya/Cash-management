import tempfile
import unittest
from pathlib import Path

import database.db as db
from database import repository
from services.analytics import current_period_stats, financial_radar, get_goal, set_goal
from services.budget import status


class RepositoryTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.original_path = db.SQLITE_PATH
        self.original_url = db.DATABASE_URL
        self.original_repository_url = repository.DATABASE_URL
        db.SQLITE_PATH = Path(self.tempdir.name) / "test.db"
        db.DATABASE_URL = ""
        repository.DATABASE_URL = ""
        db.init_db()

    def tearDown(self):
        db.SQLITE_PATH = self.original_path
        db.DATABASE_URL = self.original_url
        repository.DATABASE_URL = self.original_repository_url
        self.tempdir.cleanup()

    def test_users_have_isolated_balances_and_history(self):
        repository.add_income(101, 1000, 0)
        repository.add_income(202, 500, 0)
        self.assertTrue(repository.add_expense(101, 125, "Кафе"))

        self.assertEqual(float(repository.get_month(101)["spent"]), 125)
        self.assertEqual(float(repository.get_month(202)["spent"]), 0)
        self.assertEqual(len(repository.recent_transactions(101)), 2)
        self.assertEqual(len(repository.recent_transactions(202)), 1)

    def test_user_profile_is_available_for_mini_app_header(self):
        repository.ensure_user(101, "Алексей", "alexey")
        profile = repository.get_user_profile(101)
        self.assertEqual(profile["first_name"], "Алексей")
        self.assertEqual(profile["username"], "alexey")

    def test_main_income_has_no_withholding(self):
        fee, net, created = repository.add_income(101, 1000, 25)
        self.assertTrue(created)
        self.assertEqual(fee, 0)
        self.assertEqual(net, 1000)
        self.assertEqual(float(repository.get_month(101)["budget"]), 1000)

    def test_income_source_applies_its_own_percentage(self):
        repository.create_income_source(101, "Кафе", 6)
        self.assertIn("Кафе — <b>0 ₽</b> за месяц", status(101))
        source = repository.find_income_source(101, "получил 30000 кафе")
        self.assertIsNotNone(source)
        fee, net, created = repository.add_income_from_source(101, 30000, source["id"], "Кафе")
        self.assertTrue(created)
        self.assertEqual(fee, 1800)
        self.assertEqual(net, 28200)
        self.assertEqual(float(repository.get_month(101)["budget"]), 28200)
        stats = repository.list_income_sources(101)[0]
        self.assertEqual(float(stats["gross_total"]), 30000)
        self.assertEqual(float(stats["withheld_total"]), 1800)
        status_text = status(101)
        self.assertIn("Кафе — <b>30 000 ₽</b> за месяц · удержание <b>6%</b>", status_text)

    def test_expense_can_be_corrected_and_month_is_rebuilt(self):
        repository.add_income(101, 1000, 0)
        repository.add_expense(101, 100, "Кафе")
        expense = next(row for row in repository.recent_transactions(101) if row["kind"] == "expense")
        repository.update_expense(101, expense["id"], 75, "Продукты")
        self.assertEqual(float(repository.get_month(101)["spent"]), 75)
        corrected = next(row for row in repository.recent_transactions(101) if row["kind"] == "expense")
        self.assertEqual(corrected["description"], "Еда")

    def test_reset_only_removes_selected_user_data(self):
        repository.add_income(101, 1000, 0)
        repository.add_income(202, 500, 0)
        repository.create_income_source(101, "Кафе", 6)
        repository.reset_user_data(101)
        self.assertEqual(repository.recent_transactions(101), [])
        self.assertEqual(len(repository.recent_transactions(202)), 1)
        self.assertEqual(repository.list_income_sources(101), [])

    def test_extra_accounts_transfer_without_counting_as_expense(self):
        repository.add_income(101, 1000, 0)
        repository.create_extra_account(101, "Отпуск")
        account = repository.list_extra_accounts(101)[0]

        repository.transfer_extra_account(101, account["id"], 300, "to_account", "transfer-0001")
        snapshot = repository.get_status_snapshot(101)
        self.assertEqual(snapshot["remaining"], 700)
        self.assertEqual(snapshot["spent"], 0)
        self.assertEqual(float(repository.list_extra_accounts(101)[0]["balance"]), 300)

        repository.transfer_extra_account(101, account["id"], 125, "to_main", "transfer-0002")
        snapshot = repository.get_status_snapshot(101)
        self.assertEqual(snapshot["remaining"], 825)
        self.assertEqual(snapshot["spent"], 0)
        self.assertEqual(float(repository.list_extra_accounts(101)[0]["balance"]), 175)

    def test_extra_accounts_are_limited_and_nonempty_account_cannot_be_deleted(self):
        repository.add_income(101, 1000, 0)
        for name in ("Отпуск", "Ремонт", "Резерв"):
            repository.create_extra_account(101, name)
        with self.assertRaises(ValueError):
            repository.create_extra_account(101, "Четвёртый")

        account = repository.list_extra_accounts(101)[0]
        repository.transfer_extra_account(101, account["id"], 100, "to_account", "transfer-0003")
        with self.assertRaises(ValueError):
            repository.delete_extra_account(101, account["id"])
        repository.transfer_extra_account(101, account["id"], 100, "to_main", "transfer-0004")
        repository.delete_extra_account(101, account["id"])
        self.assertEqual(len(repository.list_extra_accounts(101)), 2)

    def test_extra_account_transfer_is_idempotent(self):
        repository.add_income(101, 1000, 0)
        repository.create_extra_account(101, "Резерв")
        account = repository.list_extra_accounts(101)[0]
        repository.transfer_extra_account(101, account["id"], 200, "to_account", "transfer-0005")
        repository.transfer_extra_account(101, account["id"], 200, "to_account", "transfer-0005")
        self.assertEqual(float(repository.list_extra_accounts(101)[0]["balance"]), 200)
        self.assertEqual(repository.get_status_snapshot(101)["remaining"], 800)

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

        today = date.today()
        self.assertEqual(repository.apply_due_recurring_payments(101, today), [])
        if today.month == 12:
            next_month = date(today.year + 1, 1, 1)
        else:
            next_month = date(today.year, today.month + 1, 1)
        self.assertEqual(len(repository.apply_due_recurring_payments(101, next_month)), 1)
        self.assertEqual(repository.apply_due_recurring_payments(101, next_month), [])
        self.assertEqual(float(repository.get_month(101)["spent"]), 120)
        recurring = [row for row in repository.recent_transactions(101) if row["kind"] == "recurring"]
        self.assertEqual(len(recurring), 1)
        stats = current_period_stats(101)
        self.assertEqual(stats["expenses"], 0)
        self.assertEqual(stats["recurring"], 120)

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

    def test_financial_radar_reserves_payments_and_compares_weeks(self):
        from datetime import date, timedelta

        today = date(2026, 9, 25)
        repository.ensure_user(101)
        with db.get_connection() as conn:
            conn.execute(
                "INSERT INTO transactions(user_id,created_at,kind,amount,description) VALUES (?, ?, 'expense', 100, 'Еда')",
                (101, today.isoformat()),
            )
            conn.execute(
                "INSERT INTO transactions(user_id,created_at,kind,amount,description) VALUES (?, ?, 'expense', 200, 'Еда')",
                (101, (today - timedelta(days=8)).isoformat()),
            )
        payments = [{
            "title": "Аренда",
            "amount": 200,
            "day_of_month": 1,
            "active": 1,
            "last_run": None,
        }]

        radar = financial_radar(101, 1000, payments, today)

        self.assertEqual(radar["reserved"], 200)
        self.assertEqual(radar["safe_today"], 32)
        self.assertEqual(radar["weekly"]["current"], 100)
        self.assertEqual(radar["weekly"]["previous"], 200)
        self.assertEqual(radar["weekly"]["change_percent"], -50)
        self.assertEqual(radar["streak"]["current"], 0)
        self.assertTrue(any(item["title"] == "Аренда" for item in radar["calendar"]))


if __name__ == "__main__":
    unittest.main()
