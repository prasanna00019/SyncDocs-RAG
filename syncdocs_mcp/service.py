from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from syncdocs_mcp.config import load_config, save_config
from syncdocs_mcp.firecrawl.mapper import map_and_filter
from syncdocs_mcp.firecrawl.scraper import batch_scrape_with_change_tracking
from syncdocs_mcp.firecrawl.search import search_web as firecrawl_search_web
from syncdocs_mcp.rag.system import RAGSystem
from syncdocs_mcp.rag.versioning import collection_name, delete_collection, list_collection_details


def infer_library_name(url: str) -> str:
    hostname = urlparse(url).netloc.lower()
    labels = [label for label in hostname.split(".") if label and label not in {"www", "docs", "developers", "developer", "api"}]
    candidate = labels[0] if labels else hostname.replace(".", "_")
    return candidate.replace("-", "_") or "docs"


class SyncDocsService:
    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or load_config()
        self._rag: RAGSystem | None = None

    @property
    def rag(self) -> RAGSystem:
        if self._rag is None:
            self._rag = RAGSystem(config=self.config)
        return self._rag

    def _reload(self) -> None:
        self.config = load_config()
        if self._rag is not None:
            self._rag.config = self.config

    def _set_active_source(self, library: str, version: str, url: str, query: str) -> None:
        self._reload()
        collection = collection_name(library, version)
        registry = dict(self.config.get("indexed_sources", {}))
        registry[collection] = {
            "library": library,
            "version": version,
            "url": url,
            "query": query,
            "last_indexed": datetime.now(timezone.utc).isoformat(),
        }
        self.config["indexed_sources"] = registry
        self.config["last_active_library"] = library
        self.config["last_active_version"] = version
        self.config = save_config(self.config)

    def resolve_target(self, library: str | None = None, version: str = "latest") -> tuple[str, str]:
        if library:
            return library, version
        if self.config.get("last_active_library"):
            return self.config["last_active_library"], self.config.get("last_active_version", "latest")
        registry = self.config.get("indexed_sources", {})
        if registry:
            first = next(iter(registry.values()))
            return first.get("library", "docs"), first.get("version", "latest")
        raise RuntimeError("No indexed collection available. Fetch and index docs first.")

    def search_web(self, query: str, limit: int = 5) -> list[dict[str, str]]:
        return firecrawl_search_web(query, limit=limit, config=self.config)

    def fetch_and_index(
        self,
        url: str,
        query: str,
        library: str | None = None,
        version: str = "latest",
        limit: int | None = None,
    ) -> dict[str, Any]:
        target_library = library or infer_library_name(url)
        crawl_limit = limit or int(self.config.get("max_urls_to_scrape", 8))
        mapped_links, selected_urls = map_and_filter(url, query, limit=crawl_limit, config=self.config)
        scrape_result = batch_scrape_with_change_tracking(
            selected_urls,
            target_library,
            version,
            max_age_ms=self.config.get("scrape_max_age_ms"),
            config=self.config,
        )
        ingest_summary = self.rag.ingest(scrape_result, target_library, version)
        if ingest_summary.get("child_chunks", 0) > 0 or ingest_summary.get("parent_chunks", 0) > 0:
            self._set_active_source(target_library, version, url, query)

        warnings: list[str] = []
        if mapped_links and not any(link.get("title") or link.get("description") for link in mapped_links):
            warnings.append(
                "Self-hosted Firecrawl map returned URL-only links. This differs from the Firecrawl cloud response shape."
            )
        if scrape_result.get("warning"):
            warnings.append(scrape_result["warning"])
        return {
            "library": target_library,
            "version": version,
            "collection": ingest_summary["collection"],
            "mapped_urls": mapped_links,
            "selected_urls": selected_urls,
            "scrape_status": scrape_result.get("job_status", ""),
            "returned_pages": scrape_result.get("returned_pages", 0),
            "missing_urls": scrape_result.get("missing_urls", []),
            "warnings": warnings,
            **ingest_summary,
        }

    def query_docs(self, query: str, library: str | None = None, version: str = "latest") -> dict[str, Any]:
        target_library, target_version = self.resolve_target(library, version)
        return self.rag.query(query, target_library, target_version)

    def refresh(self, library: str, version: str = "latest", url: str | None = None, query: str | None = None) -> dict[str, Any]:
        collection = collection_name(library, version)
        registry_entry = self.config.get("indexed_sources", {}).get(collection, {})
        source_url = url or registry_entry.get("url")
        source_query = query or registry_entry.get("query")
        if not source_url or not source_query:
            raise RuntimeError("Refresh requires a stored source URL and query, or explicit --url and --query values.")
        return self.fetch_and_index(source_url, source_query, library=library, version=version)

    def clear_collection(self, library: str, version: str = "latest") -> None:
        delete_collection(library, version)
        collection = collection_name(library, version)
        registry = dict(self.config.get("indexed_sources", {}))
        registry.pop(collection, None)
        self.config["indexed_sources"] = registry
        if self.config.get("last_active_library") == library and self.config.get("last_active_version", "latest") == version:
            self.config["last_active_library"] = ""
            self.config["last_active_version"] = "latest"
        self.config = save_config(self.config)

    def status(self) -> dict[str, Any]:
        return {
            "config": self.config,
            "collections": list_collection_details(),
            "active_collection": collection_name(*self.resolve_target()) if self.config.get("indexed_sources") else "",
        }
