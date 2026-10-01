import unittest

from tests import test_pets as fixtures
from database import db, repository
from database.pets import get_world, update_world, claim_reward
from services.pet_appearance import appearance


class AppearanceTests(unittest.TestCase):
    setUp = fixtures.PetWorldTests.setUp
    tearDown = fixtures.PetWorldTests.tearDown

    def test_five_ages_boundaries_and_unlimited_chapters(self):
        points = (0, 999, 1000, 5999, 6000, 19999, 20000, 59999, 60000, 1000000)
        self.assertEqual([appearance(xp)["age_stage"] for xp in points], [1, 1, 2, 2, 3, 3, 4, 4, 5, 5])
        self.assertEqual(appearance(6000)["age_progress"], 0)
        self.assertEqual(appearance(60000)["next_age_xp"], None)

    def test_color_is_persistent_free_and_isolated(self):
        repository.add_income(101, 1000, 0)
        claim_reward(101, "visit")
        before = repository.get_status_snapshot(101)
        update_world(101, "dragon", "Искра", True, "blue")
        db.init_db()
        world = get_world(101)
        self.assertEqual((world["color"], world["xp"], world["coins"]), ("blue", 10, 5))
        self.assertEqual(get_world(202)["color"], "original")
        self.assertEqual(repository.get_status_snapshot(101)["remaining"], before["remaining"])
        update_world(101, "cat", "", False)
        self.assertEqual(get_world(101)["color"], "blue")
        self.assertEqual(self.client.post("/api/pet/settings", json={"pet": "cat", "color": "bad"}).status_code, 409)
        self.assertEqual(get_world(101)["color"], "blue")
        repository.reset_user_data(101)
        self.assertEqual(get_world(101)["color"], "original")

    def test_api_validates_color_and_derives_age_from_saved_experience(self):
        get_world(101)
        with db.get_connection() as conn:
            conn.execute("UPDATE pet_world SET xp=20000 WHERE user_id=?", (101,))
        response = self.client.post("/api/pet/settings", json={"pet": "owl", "color": "mint"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual((response.json()["age_stage"], response.json()["color"]), (4, "mint"))
        self.assertEqual(len(response.json()["colors"]), 6)
