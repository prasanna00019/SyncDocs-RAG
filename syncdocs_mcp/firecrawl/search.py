from __future__ import annotations

from typing import Any

import requests

from syncdocs_mcp.config import load_config
from syncdocs_mcp.firecrawl.client import get_client


def _normalize_search_results(payload: Any, limit: int) -> list[dict[str, str]]:
    if isinstance(payload, dict):
        items = payload.get("data") or payload.get("results") or payload.get("links") or []
    else:
        items = getattr(payload, "data", None) or getattr(payload, "results", None) or []

    results: list[dict[str, str]] = []
    for item in items[:limit]:
        if isinstance(item, dict):
            url = item.get("url") or item.get("link") or ""
            title = item.get("title") or ""
            description = item.get("description") or item.get("snippet") or ""
        else:
            url = getattr(item, "url", "") or getattr(item, "link", "")
            title = getattr(item, "title", "")
            description = getattr(item, "description", "") or getattr(item, "snippet", "")
        if url:
            results.append({"url": url, "title": title, "description": description})
    return results


def _http_search(cfg: dict[str, Any], query: str, limit: int) -> list[dict[str, str]]:
    base_url = (cfg.get("firecrawl_url") or "http://localhost:3002").rstrip("/")
    headers = {}
    api_key = cfg.get("firecrawl_api_key")
    if api_key and api_key != "local":
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {"query": query, "limit": limit}
    for endpoint in ("/v1/search", "/search"):
        try:
            response = requests.post(f"{base_url}{endpoint}", json=payload, headers=headers, timeout=20)
            response.raise_for_status()
            return _normalize_search_results(response.json(), limit)
        except requests.RequestException:
            continue
    return []


def search_web(query: str, limit: int = 5, config: dict[str, Any] | None = None) -> list[dict[str, str]]:
    cfg = config or load_config()
    client = get_client(cfg)
    if hasattr(client, "search"):
        try:
            results = client.search(query=query, limit=limit)
            normalized = _normalize_search_results(results, limit)
            if normalized:
                return normalized
        except Exception:
            pass
    return _http_search(cfg, query, limit)
