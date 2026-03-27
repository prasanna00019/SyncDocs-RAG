from pathlib import Path
from typing import Any, Dict, List
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from syncdocs_mcp.firecrawl.mapper import map_links  # noqa: E402
from syncdocs_mcp.firecrawl.scraper import batch_scrape_with_change_tracking  # noqa: E402


class DocsCrawler:
    def map_documentation(self, url: str) -> List[Dict[str, Any]]:
        return map_links(url)

    def scrape_urls(self, urls: List[str]) -> List[Dict[str, Any]]:
        result = batch_scrape_with_change_tracking(urls, library="docs", version="latest")
        return result["pages"]
