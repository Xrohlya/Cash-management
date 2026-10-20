import io
import unittest
import logging
from contextlib import redirect_stdout
from types import SimpleNamespace

from bot.console import ActivityMiddleware, ConsoleFormatter, show_startup


class ConsoleTest(unittest.TestCase):
    def test_connection_errors_are_red_and_recovery_is_green(self):
        formatter = ConsoleFormatter(use_color=True)
        error = logging.LogRecord("test", logging.ERROR, "", 0, "lost", (), None)
        self.assertIn("\033[38;5;203m", formatter.format(error))
        restored = logging.LogRecord("test", logging.INFO, "", 0, "restored", (), None)
        restored.connection_restored = True
        self.assertIn("\033[38;5;42m", formatter.format(restored))
        self.assertNotIn("\033[", ConsoleFormatter(use_color=False).format(error))

    def test_startup_distinguishes_current_previous_and_savings(self):
        output = io.StringIO()
        with redirect_stdout(output):
            show_startup(SimpleNamespace(username="test"), [dict(
                user_id=101, first_name="Test", username="test", balance=0,
                savings=160000, period_start="2026-10-20", period_end="2026-11-19",
                previous_period="2026-09-20", previous_balance=121086.86,
            )])
        text = output.getvalue()
        self.assertIn("160 000 ₽", text)
        self.assertIn("121 086,86 ₽", text)
        self.assertIn("Прошлый период", text)

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
            show_startup(bot_info, users, webapp_url="https://example.com")

        text = output.getvalue()
        self.assertIn("@cash_test_bot", text)
        self.assertIn("Mini App: https://example.com", text)
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
