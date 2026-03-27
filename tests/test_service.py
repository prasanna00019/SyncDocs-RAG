import os
import shutil
import unittest
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

from syncdocs_mcp.service import SyncDocsService


class ServiceTests(unittest.TestCase):
    @patch("syncdocs_mcp.service.batch_scrape_with_change_tracking")
    @patch("syncdocs_mcp.service.map_and_filter")
    @patch("syncdocs_mcp.service.RAGSystem")
    def test_fetch_and_index_updates_registry(self, rag_cls, map_and_filter, scrape):
        temp_dir = Path("tests/.tmp") / f"service_{uuid.uuid4().hex}"
        old_home = os.environ.get("SYNCDOCS_HOME")
        os.environ["SYNCDOCS_HOME"] = str(temp_dir)
        try:
            rag = MagicMock()
            rag.ingest.return_value = {
                "collection": "stripe_latest",
                "pages_indexed": 1,
                "pages_skipped": 0,
                "total_urls": 1,
                "child_chunks": 2,
                "parent_chunks": 1,
            }
            rag_cls.return_value = rag
            map_and_filter.return_value = (
                [{"url": "https://docs.stripe.com/payments", "title": "", "description": ""}],
                ["https://docs.stripe.com/payments"],
            )
            scrape.return_value = {
                "pages": [{"url": "https://docs.stripe.com/payments", "markdown": "# Payments"}],
                "skipped": 0,
                "total": 1,
                "job_status": "completed",
                "returned_pages": 1,
                "missing_urls": [],
                "warning": "",
            }

            service = SyncDocsService()
            result = service.fetch_and_index("https://docs.stripe.com", "payments setup", library="stripe")

            self.assertEqual(result["collection"], "stripe_latest")
            self.assertIn("stripe_latest", service.config["indexed_sources"])
            self.assertIn("URL-only links", result["warnings"][0])
        finally:
            if old_home is None:
                os.environ.pop("SYNCDOCS_HOME", None)
            else:
                os.environ["SYNCDOCS_HOME"] = old_home
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
