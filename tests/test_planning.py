import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from backend.auth import current_user
from backend.main import app
from database import db, repository
from database.category_limits import save_category_limit
from database.planned_income import confirm_planned_income, list_planned_income, save_planned_income
from database.undo import recent_undos, undo_candidate, undo_last_operation
from services.weekly_summary import weekly_summary


class PlanningTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.original_path, self.original_url = db.SQLITE_PATH, db.DATABASE_URL
        db.SQLITE_PATH = Path(self.temporary.name) / "test.db"
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
        self.temporary.cleanup()

    def dashboard(self):
        response = self.client.get("/api/dashboard")
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_planned_income_changes_forecast_not_actual_balance(self):
        repository.add_income(101, 1000, 0)
        repository.create_income_source(101, "Cafe", 6)
        source = repository.list_income_sources(101)[0]
        save_planned_income(101, "Salary", 1000, date.today(), source["id"])
        dashboard = self.dashboard()
        self.assertEqual(dashboard["state"]["available"], 1000)
        self.assertEqual(dashboard["planning"]["expected_total"], 940)
        self.assertEqual(dashboard["planning"]["projected_with_income"], dashboard["radar"]["projected_balance"] + 940)
        self.assertEqual(len(repository.recent_transactions(101)), 1)

    def test_confirmation_posts_net_income_only_once_and_refreshes_telegram(self):
        repository.create_income_source(101, "Cafe", 6)
        source = repository.list_income_sources(101)[0]
        save_planned_income(101, "Salary", 1000, date.today(), source["id"])
        plan_id = list_planned_income(101)[0]["id"]
        for _ in range(2):
            self.assertEqual(self.client.post(f"/api/plans/{plan_id}/confirm").status_code, 200)
        self.assertEqual(repository.get_status_snapshot(101)["remaining"], 940)
        self.assertEqual(len(repository.recent_transactions(101)), 2)
        self.assertEqual(self.refresh_mock.await_count, 1)

    def test_other_user_cannot_confirm_or_edit_plan(self):
        save_planned_income(101, "Salary", 1000, date.today())
        plan_id = list_planned_income(101)[0]["id"]
        self.user_id = 202
        self.assertEqual(self.client.post(f"/api/plans/{plan_id}/confirm").status_code, 409)
        self.assertEqual(self.client.post(f"/api/plans/{plan_id}/edit", json={"title": "Other", "amount": 1, "due_date": date.today().isoformat()}).status_code, 409)
        self.assertEqual(list_planned_income(202), [])
        self.assertEqual(list_planned_income(101)[0]["amount"], 1000)

    def test_deleted_source_cannot_silently_remove_withholding(self):
        repository.create_income_source(101, "Cafe", 6)
        source = repository.list_income_sources(101)[0]
        save_planned_income(101, "Salary", 1000, date.today(), source["id"])
        plan_id = list_planned_income(101)[0]["id"]
        repository.delete_income_source(101, source["id"])
        self.assertFalse(list_planned_income(101)[0]["source_available"])
        with self.assertRaises(ValueError):
            confirm_planned_income(101, plan_id)
        self.assertEqual(repository.get_status_snapshot(101)["remaining"], 0)

    def test_limits_warn_at_80_percent_and_exclude_other_users(self):
        repository.add_income(101, 1000, 0)
        repository.add_income(202, 1000, 0)
        save_category_limit(101, "продукты", 100)
        repository.add_expense(101, 80, "продукты")
        repository.add_expense(202, 500, "продукты")
        limit = self.dashboard()["planning"]["limits"][0]
        self.assertEqual((limit["category"], limit["spent"], limit["status"]), ("Еда", 80, "yellow"))
        repository.add_expense(101, 20, "продукты")
        self.assertEqual(self.dashboard()["planning"]["limits"][0]["status"], "red")
        self.user_id = 202
        self.assertEqual(self.dashboard()["planning"]["limits"], [])

    def test_undo_restores_budget_and_keeps_complete_archived_record(self):
        repository.add_income(101, 1000, 0)
        repository.add_expense(101, 125, "продукты")
        candidate = undo_candidate(101)
        undo_last_operation(101, candidate["id"])
        self.assertEqual(repository.get_status_snapshot(101)["remaining"], 1000)
        self.assertEqual(len(repository.recent_transactions(101)), 1)
        self.assertEqual(recent_undos(101)[0]["amount"], 125)
        with db.get_connection() as conn:
            archive = conn.execute("SELECT original_data FROM operation_undo WHERE user_id=?", (101,)).fetchone()
        self.assertEqual(json.loads(archive["original_data"])["transactions"][0]["id"], candidate["id"])
        with self.assertRaises(ValueError):
            undo_last_operation(101, candidate["id"])

    def test_undo_requires_confirmation_and_rejects_stale_selection(self):
        repository.add_income(101, 1000, 0)
        candidate = undo_candidate(101)
        self.assertEqual(self.client.post("/api/operations/undo", json={"transaction_id": candidate["id"]}).status_code, 400)
        repository.add_expense(101, 100, "Food")
        self.assertEqual(self.client.post("/api/operations/undo", json={"transaction_id": candidate["id"], "confirmed": True}).status_code, 409)
        self.assertEqual(repository.get_status_snapshot(101)["remaining"], 900)

    def test_undo_other_users_id_is_rejected(self):
        repository.add_income(101, 1000, 0)
        candidate = undo_candidate(101)
        repository.add_income(202, 500, 0)
        with self.assertRaises(ValueError):
            undo_last_operation(202, candidate["id"])
        self.assertEqual(repository.get_status_snapshot(101)["remaining"], 1000)

    def test_income_undo_restores_plan_and_can_be_confirmed_again(self):
        repository.create_income_source(101, "Cafe", 6)
        source = repository.list_income_sources(101)[0]
        save_planned_income(101, "Salary", 1000, date.today(), source["id"])
        plan_id = list_planned_income(101)[0]["id"]
        confirm_planned_income(101, plan_id)
        undo_last_operation(101, undo_candidate(101)["id"])
        self.assertEqual(repository.get_status_snapshot(101)["remaining"], 0)
        self.assertEqual(list_planned_income(101)[0]["id"], plan_id)
        confirm_planned_income(101, plan_id)
        self.assertEqual(repository.get_status_snapshot(101)["remaining"], 940)

    def test_undo_savings_and_account_transfers(self):
        repository.add_income(101, 1000, 0)
        repository.add_to_savings(101, 100)
        undo_last_operation(101, undo_candidate(101)["id"])
        self.assertEqual(repository.get_savings(101), 0)
        repository.create_extra_account(101, "Reserve")
        account_id = repository.list_extra_accounts(101)[0]["id"]
        repository.transfer_extra_account(101, account_id, 300, "to_account", "account-001")
        undo_last_operation(101, undo_candidate(101)["id"])
        self.assertEqual(float(repository.list_extra_accounts(101)[0]["balance"]), 0)
        self.assertEqual(repository.get_status_snapshot(101)["remaining"], 1000)

    def test_failed_undo_rolls_back_all_changes(self):
        repository.add_income(101, 1000, 0)
        repository.add_to_savings(101, 100)
        candidate = undo_candidate(101)
        with db.get_connection() as conn:
            conn.execute("UPDATE months SET budget=-1 WHERE user_id=?", (101,))
        with self.assertRaises(ValueError):
            undo_last_operation(101, candidate["id"])
        self.assertEqual(repository.get_savings(101), 100)
        self.assertEqual(len(repository.recent_transactions(101)), 2)
        self.assertEqual(recent_undos(101), [])

    def test_weekly_summary_keeps_recurring_separate_and_ignores_expected_income(self):
        repository.add_income(101, 1000, 0)
        repository.add_expense(101, 100, "Food")
        repository.add_recurring_charge(101, 50, "Internet")
        save_planned_income(101, "Future", 50000, date.today() + timedelta(days=1))
        weekly = weekly_summary(101)
        self.assertEqual((weekly["spent"], weekly["payments"], weekly["net_income"]), (100, 50, 1000))

    def test_reset_clears_new_features_only_for_selected_user(self):
        for user_id in (101, 202):
            save_planned_income(user_id, "Salary", 1000, date.today())
            save_category_limit(user_id, "Food", 100)
        repository.reset_user_data(101)
        self.assertEqual(list_planned_income(101), [])
        self.assertEqual(len(list_planned_income(202)), 1)
