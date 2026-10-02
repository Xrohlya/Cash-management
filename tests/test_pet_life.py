import unittest
import time
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
from tests import test_pets as fixtures
from database import db, repository
from database.pets import get_world, buy_item
from database.pet_life import start_game, finish_game, save_layout
from services.pet_seasons import season
from datetime import date


class PetLifeTests(unittest.TestCase):
    setUp = fixtures.PetWorldTests.setUp
    tearDown = fixtures.PetWorldTests.tearDown

    def test_layout_requires_owned_items_and_is_isolated(self):
        with self.assertRaises(ValueError): save_layout(101, {"plant": {"x": 10, "y": 20}})
        get_world(101)
        with db.get_connection() as conn:
            conn.execute("UPDATE pet_world SET coins=300 WHERE user_id=101")
        buy_item(101, "plant")
        save_layout(101, {"plant": {"x": 15, "y": 30}})
        self.assertEqual(get_world(101)["layout"]["plant"], {"x": 15, "y": 30})
        self.assertEqual(get_world(202)["layout"], {})
        self.assertEqual(self.client.post("/api/pet/layout", json={"positions": {"plant": {"x": 100, "y": 20}}}).status_code, 422)

    def test_game_verifies_time_result_owner_and_awards_once(self):
        now = time.time()
        with patch("database.pet_life.time.time", return_value=now): run = start_game(101)
        with patch("database.pet_life.time.time", return_value=now + 1):
            with self.assertRaises(ValueError): finish_game(101, run["token"], run["sequence"])
        with patch("database.pet_life.time.time", return_value=now + 10):
            with self.assertRaises(ValueError): finish_game(202, run["token"], run["sequence"])
            with self.assertRaises(ValueError): finish_game(101, run["token"], [99] * 8)
            with ThreadPoolExecutor(max_workers=3) as pool:
                results = list(pool.map(lambda _: finish_game(101, run["token"], run["sequence"]), range(3)))
        self.assertEqual(sum(results), 1)
        self.assertEqual((get_world(101)["coins"], get_world(101)["xp"]), (2, 0))
        with self.assertRaises(ValueError): start_game(101)

    def test_album_records_ages_and_goal_once_without_money_changes(self):
        repository.add_income(101, 1000, 0)
        repository.add_to_savings(101, 100)
        with db.get_connection() as conn:
            conn.execute("INSERT INTO goals(user_id,target,target_date) VALUES (?,?,?)", (101, 100, "2027-01-01"))
            conn.execute("UPDATE pet_world SET xp=60000 WHERE user_id=101")
        # Create profile before setting the experience on a new user.
        get_world(101)
        with db.get_connection() as conn: conn.execute("UPDATE pet_world SET xp=60000 WHERE user_id=101")
        first = get_world(101); second = get_world(101)
        self.assertEqual(len(first["album"]), 6)
        self.assertEqual(first["album"], second["album"])
        self.assertTrue(first["goal_badge"])
        self.assertFalse(get_world(202)["goal_badge"])
        self.assertEqual(repository.get_status_snapshot(101)["savings"], 100)
        repository.reset_user_data(101)
        self.assertEqual(get_world(101)["layout"], {})
        self.assertEqual(len(get_world(101)["album"]), 1)

    def test_seasons_recur_and_offseason_purchase_is_rejected(self):
        self.assertEqual([season(date(2026, month, 1))["id"] for month in (1,4,7,10)], ["winter","spring","summer","autumn"])
        self.assertEqual(season(date(2026,12,1))["id"], "winter")
        with patch("database.pets.season", return_value={"id": "winter"}):
            with self.assertRaises(ValueError): buy_item(101, "flower")

    def test_new_routes_are_authenticated(self):
        from backend.main import app
        app.dependency_overrides.clear()
        for path, body in (("/api/pet/layout", {"positions": {}}), ("/api/pet/game/start", {}), ("/api/pet/game/finish", {"token": "x", "sequence": [1]*8})):
            self.assertEqual(self.client.post(path, json=body).status_code, 401)

    def test_game_api_and_expiration(self):
        now = time.time()
        with patch("database.pet_life.time.time", return_value=now):
            run = self.client.post("/api/pet/game/start").json()
        body = {"token": run["token"], "sequence": run["sequence"]}
        with patch("database.pet_life.time.time", return_value=now + 121):
            self.assertEqual(self.client.post("/api/pet/game/finish", json=body).status_code, 409)
        with patch("database.pet_life.time.time", return_value=now + 10):
            response = self.client.post("/api/pet/game/finish", json=body)
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.json()["world"]["minigame_claimed"])
        self.assertEqual(self.client.post("/api/pet/layout", json={"positions": {"plant": {"x": "NaN", "y": 20}}}).status_code, 422)
