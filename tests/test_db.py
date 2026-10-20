import unittest
from unittest.mock import Mock, patch
from psycopg import OperationalError
from services.connection_status import ConnectionStatus

from database import db


class DatabaseStartupTest(unittest.TestCase):
    def test_query_failure_and_recovery_are_reported_without_replaying_writes(self):
        cursor = Mock()
        cursor.execute.side_effect = [OperationalError("connection lost"), None]
        connection = Mock()
        connection.cursor.return_value = cursor
        status = ConnectionStatus("Test database")
        with patch.object(db, "database_connection", status), self.assertLogs(level="INFO") as logs:
            wrapper = db._PGConnection(connection)
            with self.assertRaises(OperationalError):
                wrapper.execute("SELECT 1")
            self.assertEqual(cursor.execute.call_count, 1)
            wrapper.execute("SELECT 1")
        self.assertEqual(len(logs.records), 2)
        self.assertIn("СВЯЗЬ ПОТЕРЯНА", logs.records[0].getMessage())
        self.assertTrue(logs.records[1].connection_restored)

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
