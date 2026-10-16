import unittest

from bot import keyboards
from config.settings import WEBAPP_RELEASE


class MainMenuTest(unittest.TestCase):
    def test_main_menu_has_expected_two_column_layout(self):
        original_url = keyboards.WEBAPP_URL
        keyboards.WEBAPP_URL = "https://example.com"
        try:
            rows = keyboards.main_menu().inline_keyboard
        finally:
            keyboards.WEBAPP_URL = original_url

        self.assertEqual([button.text for button in rows[0]], ["Открыть приложение"])
        self.assertEqual(rows[0][0].web_app.url, f"https://example.com?v={WEBAPP_RELEASE}")
        self.assertEqual(
            [[button.callback_data for button in row] for row in rows[1:]],
            [
                ["status", "today"],
                ["history", "status"],
                ["help"],
            ],
        )

    def test_nested_actions_have_budget_return(self):
        for menu, expected in ((keyboards.help_menu, ["clear_chat"]),
                               (keyboards.history_menu, ["report", "excel"])):
            with self.subTest(menu=menu.__name__):
                rows = [row for row in menu().inline_keyboard if not any(b.web_app for b in row)]
                self.assertEqual([[b.callback_data for b in row] for row in rows], [expected, ["status"]])


if __name__ == "__main__":
    unittest.main()
