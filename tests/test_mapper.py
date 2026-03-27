import unittest

from syncdocs_mcp.firecrawl.mapper import select_relevant_urls


class MapperTests(unittest.TestCase):
    def test_preserves_ranked_links_when_metadata_exists(self):
        links = [
            {"url": "https://example.com/setup", "title": "Setup", "description": "Install guide"},
            {"url": "https://example.com/auth", "title": "Auth", "description": "Authentication"},
        ]
        selected = select_relevant_urls("how to install", links, limit=2)
        self.assertEqual(selected, ["https://example.com/setup", "https://example.com/auth"])

    def test_slug_fallback_filters_when_titles_missing(self):
        links = [
            {"url": "https://example.com/reference/webhooks", "title": "", "description": ""},
            {"url": "https://example.com/guides/payments/setup", "title": "", "description": ""},
            {"url": "https://example.com/changelog", "title": "", "description": ""},
        ]
        selected = select_relevant_urls("payment setup", links, limit=2)
        self.assertEqual(selected[0], "https://example.com/guides/payments/setup")


if __name__ == "__main__":
    unittest.main()
