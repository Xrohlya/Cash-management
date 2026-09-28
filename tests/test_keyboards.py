import unittest

from bot import keyboards


class MainMenuTest(unittest.TestCase):
    def test_main_menu_has_expected_two_column_layout(self):
        original_url = keyboards.WEBAPP_URL
        keyboards.WEBAPP_URL = "https://example.com"
        try:
            rows = keyboards.main_menu().inline_keyboard
        finally:
            keyboards.WEBAPP_URL = original_url

        self.assertEqual([button.text for button in rows[0]], ["Открыть приложение"])
        self.assertEqual(
            [[button.callback_data for button in row] for row in rows[1:]],
            [
                ["status", "today"],
                ["history", "forecast"],
                ["savings", "goal"],
                ["recurring", "income_sources"],
                ["analytics", "compare"],
                ["help", "clear_chat"],
                ["report", "status"],
            ],
        )


if __name__ == "__main__":
    unittest.main()
