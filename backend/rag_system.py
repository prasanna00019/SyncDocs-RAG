from pathlib import Path
from typing import Any, Dict, List
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from syncdocs_mcp.rag.system import RAGSystem as _RAGSystem  # noqa: E402


class RAGSystem(_RAGSystem):
    def chunk_and_ingest(self, scraped_data: List[Dict[str, Any]], library: str = "docs", version: str = "latest"):
        return self.ingest(scraped_data, library=library, version=version)

    def query(self, user_query: str, library: str | None = None, version: str = "latest"):
        result = super().query(user_query, library=library, version=version)
        return result["answer"]
