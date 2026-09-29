import io
import unittest
from contextlib import redirect_stdout
from types import SimpleNamespace

from bot.console import ActivityMiddleware, show_startup


class ConsoleTest(unittest.TestCase):
    def test_startup_shows_bot_and_user_summary(self):
        bot_info = SimpleNamespace(username="cash_test_bot")
        users = [{
            "user_id": 123456,
            "first_name": "Алексей",
            "username": "alexey",
            "balance": 875,
        }]

        output = io.StringIO()
        with redirect_stdout(output):
            show_startup(bot_info, users)

        text = output.getvalue()
        self.assertIn("@cash_test_bot", text)
        self.assertIn("Пользователей: 1", text)
        self.assertIn("123456", text)
        self.assertIn("Алексей · @alexey", text)
        self.assertIn("875 ₽", text)

    def test_activity_line_shows_identity_action_and_timing(self):
        user = SimpleNamespace(id=123456, first_name="Алексей", username="alexey")

        output = io.StringIO()
        with redirect_stdout(output):
            ActivityMiddleware._print(user, "обновил бюджет", 0.125, True)

        text = output.getvalue()
        self.assertIn("Алексей · @alexey [123456]", text)
        self.assertIn("обновил бюджет", text)
        self.assertIn("125 мс", text)


if __name__ == "__main__":
    unittest.main()
