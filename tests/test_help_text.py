import unittest
from html.parser import HTMLParser

from bot.texts import HELP
from services.parser import looks_like_income, parse_expense
from services.wallet_commands import parse_wallet_command


class HelpMarkup(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []

    def handle_starttag(self, tag, attrs):
        if tag not in {"b", "code"} or attrs:
            raise AssertionError(f"Unexpected help tag: {tag}")
        self.stack.append(tag)

    def handle_endtag(self, tag):
        if not self.stack or self.stack.pop() != tag:
            raise AssertionError(f"Unbalanced help tag: {tag}")


class HelpTextTests(unittest.TestCase):
    def test_help_fits_one_message_and_has_balanced_markup(self):
        self.assertLessEqual(len(HELP), 4096)
        markup = HelpMarkup()
        markup.feed(HELP)
        self.assertEqual(markup.stack, [])
        for number in range(1, 8):
            self.assertIn(f"<b>{number}.", HELP)

    def test_quick_examples_are_understood(self):
        self.assertEqual(parse_expense("кофе 300"), (300, "кофе"))
        self.assertTrue(looks_like_income("получил 30000 кафе"))
        self.assertIn("кофе 300", HELP)
        self.assertIn("получил 30000 кафе", HELP)

    def test_documented_wallet_examples_resolve(self):
        accounts = [{"id": 1, "name": "Отпуск"}]
        for text in (
            "перевод 3000 с основного на счет Отпуск",
            "перевод 500 со счета Отпуск на основной",
            "перевод 1000 из накоплений на основной",
            "расход 500 со счета Отпуск такси",
            "расход 500 из накоплений ремонт",
            "возврат 500 Разное",
        ):
            with self.subTest(text=text):
                self.assertIn(text, HELP)
                parse_wallet_command(text, accounts)
