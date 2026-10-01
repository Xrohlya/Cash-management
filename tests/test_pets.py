import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from pathlib import Path

from fastapi.testclient import TestClient
from backend.auth import current_user
from backend.main import app
from database import db, repository
from database.pets import buy_item, claim_reward, get_world, update_world
from services.pet_catalog import progression


class PetWorldTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.original_path, self.original_url = db.SQLITE_PATH, db.DATABASE_URL
        db.SQLITE_PATH, db.DATABASE_URL = Path(self.temporary.name) / "pets.db", ""
        db.init_db()
        self.user_id = 101
        app.dependency_overrides[current_user] = lambda: self.user_id
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()
        db.SQLITE_PATH, db.DATABASE_URL = self.original_path, self.original_url
        self.temporary.cleanup()

    def test_default_profile_has_five_choices_and_no_rewards_on_read(self):
        first = self.client.get("/api/pet").json()
        second = get_world(101)
        self.assertEqual(len(first["pets"]), 5)
        self.assertEqual((first["xp"], second["coins"]), (0, 0))
        self.assertEqual(first["inventory"], [])

    def test_reward_is_once_a_day_and_never_changes_money(self):
        repository.add_income(101, 1000, 0)
        before = repository.get_status_snapshot(101)
        self.assertTrue(claim_reward(101, "visit"))
        self.assertFalse(claim_reward(101, "visit"))
        after = repository.get_status_snapshot(101)
        self.assertEqual((after["remaining"], after["savings"]), (before["remaining"], before["savings"]))
        self.assertEqual((get_world(101)["xp"], get_world(101)["coins"]), (10, 5))
        self.assertEqual(len(repository.recent_transactions(101)), 1)

    def test_concurrent_claims_grant_one_reward(self):
        with ThreadPoolExecutor(max_workers=4) as pool:
            granted = list(pool.map(lambda _: claim_reward(101, "visit"), range(4)))
        self.assertEqual(sum(granted), 1)
        self.assertEqual(get_world(101)["coins"], 5)

    def test_missions_require_actual_today_operations(self):
        self.assertEqual(self.client.post("/api/pet/claim", json={"id": "record"}).status_code, 409)
        repository.add_income(101, 1000, 0)
        self.assertTrue(claim_reward(101, "record"))
        self.assertEqual(self.client.post("/api/pet/claim", json={"id": "save"}).status_code, 409)
        repository.add_to_savings(101, 100)
        self.assertTrue(claim_reward(101, "save"))

    def test_old_or_other_users_operations_do_not_complete_mission(self):
        repository.add_income(101, 1000, 0)
        repository.add_income(202, 1000, 0)
        repository.add_to_savings(202, 100)
        with db.get_connection() as conn:
            conn.execute("UPDATE transactions SET created_at=? WHERE user_id=?", ((date.today() - timedelta(days=1)).isoformat() + "T12:00:00", 101))
        missions = {item["id"]: item for item in get_world(101)["missions"]}
        self.assertFalse(missions["record"]["eligible"])
        self.assertFalse(missions["save"]["eligible"])

    def test_store_rejects_insufficient_coins_and_duplicate_purchase(self):
        with self.assertRaises(ValueError):
            buy_item(101, "plant")
        claim_reward(101, "visit")
        repository.add_income(101, 500, 0)
        claim_reward(101, "record")
        self.assertTrue(buy_item(101, "plant"))
        self.assertFalse(buy_item(101, "plant"))
        self.assertEqual(get_world(101)["coins"], 0)
        self.assertEqual(repository.get_status_snapshot(101)["remaining"], 500)
        self.assertEqual(get_world(202)["inventory"], [])

    def test_concurrent_purchase_only_charges_once(self):
        get_world(101)
        with db.get_connection() as conn:
            conn.execute("UPDATE pet_world SET coins=20 WHERE user_id=?", (101,))
        with ThreadPoolExecutor(max_workers=3) as pool:
            purchased = list(pool.map(lambda _: buy_item(101, "plant"), range(3)))
        self.assertEqual(sum(purchased), 1)
        self.assertEqual(get_world(101)["coins"], 10)

    def test_switch_and_settings_preserve_progress_and_isolation(self):
        claim_reward(101, "visit")
        update_world(101, "owl", "Луна", False)
        world = get_world(101)
        self.assertEqual((world["pet"], world["display_name"], world["motion"], world["xp"]), ("owl", "Луна", 0, 10))
        self.assertEqual(get_world(202)["pet"], "robot")
        self.assertEqual(self.client.post("/api/pet/settings", json={"pet": "invalid"}).status_code, 409)

    def test_room_progress_thresholds_and_no_decay(self):
        self.assertEqual([progression(xp)["stage"] for xp in (0, 99, 100, 249, 250)], [1, 1, 2, 2, 3])
        self.assertEqual(progression(350)["progress"], 100)

    def test_reset_and_repeat_schema_preserve_other_user(self):
        claim_reward(101, "visit")
        claim_reward(202, "visit")
        db.init_db()
        self.assertEqual(get_world(101)["xp"], 10)
        repository.reset_user_data(101)
        self.assertEqual(get_world(101)["xp"], 0)
        self.assertEqual(get_world(202)["xp"], 10)

    def test_routes_require_authentication(self):
        app.dependency_overrides.clear()
        for path, body in (("/api/pet/settings", {"pet": "cat"}), ("/api/pet/claim", {"id": "visit"}), ("/api/pet/buy", {"id": "plant"})):
            self.assertEqual(self.client.post(path, json=body).status_code, 401)
        self.assertEqual(self.client.get("/api/pet").status_code, 401)
