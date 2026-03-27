import unittest
from unittest.mock import patch

from syncdocs_mcp.firecrawl.scraper import batch_scrape_with_change_tracking


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class ScraperTests(unittest.TestCase):
    @patch("syncdocs_mcp.firecrawl.scraper.time.sleep", return_value=None)
    @patch("syncdocs_mcp.firecrawl.scraper.requests.get")
    @patch("syncdocs_mcp.firecrawl.scraper.requests.post")
    def test_polls_batch_job_and_extracts_pages(self, post_mock, get_mock, _sleep_mock):
        post_mock.return_value = _FakeResponse(
            {
                "success": True,
                "id": "job-123",
                "url": "http://localhost:3002/v2/batch/scrape/job-123",
            }
        )
        get_mock.return_value = _FakeResponse(
            {
                "success": True,
                "status": "completed",
                "completed": 1,
                "total": 1,
                "data": [
                    {
                        "markdown": "# Overview",
                        "metadata": {
                            "sourceURL": "https://docs.example.com/overview",
                            "title": "Overview",
                        },
                        "changeTracking": {"changeStatus": "new"},
                    }
                ],
            }
        )

        result = batch_scrape_with_change_tracking(
            ["https://docs.example.com/overview"],
            "example",
            "latest",
            config={"firecrawl_url": "http://localhost:3002", "firecrawl_api_key": "local", "only_main_content": True},
        )

        self.assertEqual(result["job_status"], "completed")
        self.assertEqual(len(result["pages"]), 1)
        self.assertEqual(result["pages"][0]["url"], "https://docs.example.com/overview")
        self.assertEqual(result["missing_urls"], [])

    @patch("syncdocs_mcp.firecrawl.scraper.time.sleep", return_value=None)
    @patch("syncdocs_mcp.firecrawl.scraper.requests.get")
    @patch("syncdocs_mcp.firecrawl.scraper.requests.post")
    def test_reports_warning_when_firecrawl_returns_no_pages(self, post_mock, get_mock, _sleep_mock):
        post_mock.return_value = _FakeResponse(
            {
                "success": True,
                "id": "job-456",
                "url": "http://localhost:3002/v2/batch/scrape/job-456",
            }
        )
        get_mock.return_value = _FakeResponse(
            {
                "success": True,
                "status": "completed",
                "completed": 0,
                "total": 0,
                "data": [],
            }
        )

        result = batch_scrape_with_change_tracking(
            ["https://docs.example.com/blocked"],
            "example",
            "latest",
            config={"firecrawl_url": "http://localhost:3002", "firecrawl_api_key": "local", "only_main_content": True},
        )

        self.assertEqual(result["pages"], [])
        self.assertIn("blocked scraping", result["warning"])
        self.assertEqual(result["missing_urls"], ["https://docs.example.com/blocked"])

    @patch("syncdocs_mcp.firecrawl.scraper.time.sleep", return_value=None)
    @patch("syncdocs_mcp.firecrawl.scraper.requests.get")
    @patch("syncdocs_mcp.firecrawl.scraper.requests.post")
    def test_falls_back_to_markdown_only_when_change_tracking_is_empty(self, post_mock, get_mock, _sleep_mock):
        post_mock.side_effect = [
            _FakeResponse(
                {
                    "success": True,
                    "id": "job-change-tracking",
                    "url": "http://localhost:3002/v2/batch/scrape/job-change-tracking",
                }
            ),
            _FakeResponse(
                {
                    "success": True,
                    "id": "job-markdown",
                    "url": "http://localhost:3002/v2/batch/scrape/job-markdown",
                }
            ),
        ]
        get_mock.side_effect = [
            _FakeResponse({"success": True, "status": "completed", "completed": 0, "total": 1, "data": []}),
            _FakeResponse(
                {
                    "success": True,
                    "status": "completed",
                    "completed": 1,
                    "total": 1,
                    "data": [
                        {
                            "markdown": "# Overview",
                            "metadata": {"sourceURL": "https://docs.example.com/overview"},
                            "changeTracking": {"changeStatus": "new"},
                        }
                    ],
                }
            ),
        ]

        result = batch_scrape_with_change_tracking(
            ["https://docs.example.com/overview"],
            "example",
            "latest",
            config={"firecrawl_url": "http://localhost:3002", "firecrawl_api_key": "local", "only_main_content": True},
        )

        self.assertEqual(len(result["pages"]), 1)
        self.assertIn("markdown-only scraping", result["warning"])


if __name__ == "__main__":
    unittest.main()
