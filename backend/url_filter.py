from pathlib import Path
from typing import Any, Dict, List
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from syncdocs_mcp.firecrawl.mapper import select_relevant_urls  # noqa: E402


class URLFilter:
    def filter_urls(self, query: str, mapped_urls: List[Dict[str, Any]], max_urls_to_send: int = 150) -> List[str]:
        limit = min(max_urls_to_send, len(mapped_urls)) if mapped_urls else 0
        return select_relevant_urls(query, mapped_urls, limit=limit or 0)
