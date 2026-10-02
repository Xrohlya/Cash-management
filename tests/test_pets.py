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
        with db.get_connection() as conn:
            conn.execute("UPDATE pet_world SET coins=300 WHERE user_id=?", (101,))
        self.assertTrue(buy_item(101, "plant"))
        self.assertFalse(buy_item(101, "plant"))
        self.assertEqual(get_world(101)["coins"], 0)
        self.assertEqual(repository.get_status_snapshot(101)["remaining"], 500)
        self.assertEqual(get_world(202)["inventory"], [])

    def test_concurrent_purchase_only_charges_once(self):
        get_world(101)
        with db.get_connection() as conn:
            conn.execute("UPDATE pet_world SET coins=600 WHERE user_id=?", (101,))
        with ThreadPoolExecutor(max_workers=3) as pool:
            purchased = list(pool.map(lambda _: buy_item(101, "plant"), range(3)))
        self.assertEqual(sum(purchased), 1)
        self.assertEqual(get_world(101)["coins"], 300)

    def test_same_character_settings_preserve_progress_and_isolation(self):
        update_world(101, "owl", "", True)
        claim_reward(101, "visit")
        update_world(101, "owl", "Луна", False)
        world = get_world(101)
        self.assertEqual((world["pet"], world["display_name"], world["motion"], world["xp"]), ("owl", "Луна", 0, 10))
        self.assertEqual(get_world(202)["pet"], "robot")
        self.assertEqual(self.client.post("/api/pet/settings", json={"pet": "invalid"}).status_code, 409)

    def test_room_progress_thresholds_and_no_decay(self):
        self.assertEqual([progression(xp)["stage"] for xp in (0, 2999, 3000, 17999, 18000)], [1, 1, 2, 2, 3])
        self.assertEqual(progression(18000)["next_stage_xp"], 36000)
        self.assertEqual(progression(36000)["chapter"], 2)
        self.assertEqual(progression(36000)["progress"], 0)

    def test_upgrades_charge_once_per_tier_and_preserve_legacy_items(self):
        get_world(101)
        with db.get_connection() as conn:
            conn.execute("UPDATE pet_world SET coins=2000 WHERE user_id=?", (101,))
            conn.execute("INSERT INTO pet_inventory(user_id,item) VALUES (?,?)", (101, "plant"))
        plant = next(item for item in get_world(101)["shop"] if item["id"] == "plant")
        self.assertEqual((plant["tier"], plant["cost"]), (1, 450))
        self.assertTrue(buy_item(101, "plant", 1))
        self.assertFalse(buy_item(101, "plant", 1))
        self.assertTrue(buy_item(101, "plant", 2))
        self.assertFalse(buy_item(101, "plant", 3))
        self.assertEqual(get_world(101)["coins"], 875)
        self.assertEqual(get_world(101)["upgrades"]["plant"], 3)
        self.assertEqual(get_world(101)["inventory"], ["plant"])
        self.assertEqual(get_world(202)["upgrades"], {})

    def test_growth_is_bounded_and_rewards_are_unchanged(self):
        from services.pet_catalog import MISSIONS
        sizes = [progression(xp)["size"] for xp in (0, 1000, 6000, 20000, 60000, 1000000)]
        self.assertEqual(sizes, sorted(sizes))
        self.assertEqual((sizes[0], sizes[-1]), (0.65, 1.05))
        self.assertEqual({key: (value["xp"], value["coins"]) for key, value in MISSIONS.items()},
                         {"feed": (10, 0), "visit": (10, 5), "record": (15, 5), "save": (20, 10)})

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

    def test_feeding_uses_completed_day_once_without_spending_money(self):
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        repository.add_income(101, 1000, 0)
        with db.get_connection() as conn:
            conn.execute("INSERT INTO pet_daily_budget(user_id,day,allowance) VALUES (?,?,?)", (101, yesterday, 100))
            conn.execute("INSERT INTO transactions(user_id,created_at,kind,amount,description) VALUES (?,?,?,?,?)", (101, yesterday + "T12:00:00", "expense", 40, "test"))
        task = next(item for item in get_world(101)["missions"] if item["id"] == "feed")
        self.assertEqual((task["eligible"], task["remaining"], task["title"]), (True, 60, "Лакомство"))
        before = repository.get_status_snapshot(101)["remaining"]
        self.assertTrue(claim_reward(101, "feed"))
        self.assertFalse(claim_reward(101, "feed"))
        self.assertEqual(repository.get_status_snapshot(101)["remaining"], before)

    def test_no_feed_without_recorded_day_or_remaining_allowance(self):
        with self.assertRaises(ValueError):
            claim_reward(101, "feed")
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        with db.get_connection() as conn:
            conn.execute("INSERT INTO pet_daily_budget(user_id,day,allowance) VALUES (?,?,?)", (101, yesterday, 0))
        with self.assertRaises(ValueError):
            claim_reward(101, "feed")

    def test_recorded_allowance_is_not_increased_by_refresh(self):
        from database.pet_feeding import remember_daily_limit
        remember_daily_limit(101, 100, 20)
        remember_daily_limit(101, 900, 30)
        with db.get_connection() as conn:
            row = conn.execute("SELECT allowance FROM pet_daily_budget WHERE user_id=?", (101,)).fetchone()
        self.assertEqual(row["allowance"], 120)

    def test_spending_does_not_inflate_original_daily_limit(self):
        from database.pet_feeding import remember_daily_limit
        remember_daily_limit(101, 10, 900, 10)
        with db.get_connection() as conn:
            row = conn.execute("SELECT allowance FROM pet_daily_budget WHERE user_id=?", (101,)).fetchone()
        self.assertEqual(row["allowance"], 100)
