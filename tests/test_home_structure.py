import unittest
from collections import Counter
from html.parser import HTMLParser

from backend.webapp import webapp_html


class Elements(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.elements = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))


class HomeStructureTests(unittest.TestCase):
    def setUp(self):
        self.elements = Elements(webapp_html()).elements
        self.by_id = {attrs["id"]: (tag, attrs) for tag, attrs in self.elements if "id" in attrs}

    def test_unique_ids_and_existing_navigation_targets(self):
        counts = Counter(attrs["id"] for _, attrs in self.elements if "id" in attrs)
        self.assertFalse([key for key, count in counts.items() if count > 1])
        for _, attrs in self.elements:
            for attribute in ("aria-controls", "data-budget-jump"):
                if attribute in attrs:
                    self.assertIn(attrs[attribute], self.by_id)

    def test_four_main_tabs_and_separate_settings(self):
        tabs = [attrs["data-tab-target"] for _, attrs in self.elements if attrs.get("role") == "tab"]
        self.assertEqual(tabs, ["budget", "expenses", "plans", "pets"])
        self.assertEqual(self.by_id["nav-settings"][1]["data-tab-target"], "settings")

    def test_single_transfer_form_and_collapsible_wallet_panels(self):
        self.assertNotIn("account-transfer-dialog", self.by_id)
        for panel in ("wallet-transfer-panel", "wallet-refund-panel"):
            tag, attrs = self.by_id[panel]
            self.assertEqual(tag, "details")
            self.assertNotIn("open", attrs)
        self.assertIn("wallet-transfer-form", self.by_id)
        self.assertIn("save-destination", self.by_id)
