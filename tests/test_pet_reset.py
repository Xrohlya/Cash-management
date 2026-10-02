import unittest

from database import db, repository
from database.pets import get_world, update_world, claim_reward
from database.pet_reset import change_character, GAME_TABLES
from tests import test_pets as fixtures


class CharacterResetTests(unittest.TestCase):
    setUp = fixtures.PetWorldTests.setUp
    tearDown = fixtures.PetWorldTests.tearDown

    def test_selection_locks_but_name_and_color_can_change(self):
        update_world(101, "cat", "", True)
        with self.assertRaises(ValueError):
            update_world(101, "owl", "", True)
        update_world(101, "cat", "Kit", False)
        self.assertEqual(get_world(101)["name"], "Kit")

    def test_character_change_clears_only_own_game(self):
        repository.add_income(101, 1000, 0)
        update_world(101, "cat", "Kit", True)
        claim_reward(101, "visit")
        claim_reward(202, "visit")
        before = repository.get_status_snapshot(101)
        with self.assertRaises(ValueError):
            change_character(101, "owl", "cat", "")
        change_character(101, "owl", "cat", "СМЕНИТЬ ПЕРСОНАЖА")
        world = get_world(101)
        self.assertEqual((world["pet"], world["xp"], world["coins"], world["name"]), ("owl", 0, 0, ""))
        self.assertEqual(world["inventory"], [])
        self.assertEqual(get_world(202)["xp"], 10)
        self.assertEqual(repository.get_status_snapshot(101), before)
        with self.assertRaises(ValueError):
            change_character(101, "owl", "cat", "СМЕНИТЬ ПЕРСОНАЖА")

    def test_full_reset_clears_all_game_tables(self):
        repository.add_income(101, 1000, 0)
        update_world(101, "cat", "", True)
        claim_reward(101, "visit")
        repository.reset_user_data(101)
        with db.get_connection() as conn:
            for table in GAME_TABLES:
                self.assertEqual(conn.execute(f"SELECT COUNT(*) AS n FROM {table} WHERE user_id=?", (101,)).fetchone()["n"], 0)
        self.assertEqual(repository.recent_transactions(101), [])
