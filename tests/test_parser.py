import unittest
from datetime import date

from services.parser import extract_date, parse_expense


class ParserTest(unittest.TestCase):
    def test_amount_before_description(self):
        self.assertEqual(parse_expense("1250 продукты"), (1250.0, "продукты"))

    def test_amount_after_description(self):
        self.assertEqual(parse_expense("такси 800"), (800.0, "такси"))

    def test_currency_words_are_removed(self):
        self.assertEqual(parse_expense("500 рублей еда"), (500.0, "еда"))

    def test_relative_date(self):
        self.assertEqual(extract_date("кофе вчера 300", date(2026, 9, 25)), date(2026, 9, 24))


if __name__ == "__main__":
    unittest.main()
