import unittest
from unittest.mock import patch

from database import db


class DatabaseStartupTest(unittest.TestCase):
    @patch("database.db.time.sleep")
    @patch("database.db.close_db_pool")
    @patch("database.db._init_db_once", side_effect=[RuntimeError("network"), None])
    def test_initialization_retries_after_transient_failure(
        self, init_once, close_pool, sleep
    ):
        db.init_db(attempts=3)

        self.assertEqual(init_once.call_count, 2)
        close_pool.assert_called_once_with()
        sleep.assert_called_once_with(2)

    @patch("database.db.time.sleep")
    @patch("database.db.close_db_pool")
    @patch("database.db._init_db_once", side_effect=RuntimeError("offline"))
    def test_initialization_raises_after_last_attempt(
        self, init_once, close_pool, sleep
    ):
        with self.assertRaisesRegex(RuntimeError, "offline"):
            db.init_db(attempts=3)

        self.assertEqual(init_once.call_count, 3)
        self.assertEqual(close_pool.call_count, 3)
        self.assertEqual(sleep.call_count, 2)


if __name__ == "__main__":
    unittest.main()
