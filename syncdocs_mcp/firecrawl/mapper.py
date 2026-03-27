from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

import requests

from syncdocs_mcp.config import load_config
from syncdocs_mcp.firecrawl.client import get_client


def _normalize_links(payload: Any) -> list[dict[str, str]]:
    if isinstance(payload, dict):
        raw_links = payload.get("links", [])
    else:
        raw_links = getattr(payload, "links", [])

    links: list[dict[str, str]] = []
    for item in raw_links:
        if isinstance(item, dict):
            url = item.get("url") or ""
            title = item.get("title") or ""
            description = item.get("description") or ""
        else:
            url = getattr(item, "url", "") or str(item)
            title = getattr(item, "title", "") or ""
            description = getattr(item, "description", "") or ""
        if url:
            links.append({"url": url, "title": title, "description": description})
    return links


def map_links(
    url: str,
    query: str | None = None,
    max_results: int = 100,
    config: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    cfg = config or load_config()
    kwargs: dict[str, Any] = {"url": url, "limit": max_results}
    if query:
        kwargs["search"] = query

    try:
        client = get_client(cfg)
        result = client.map(**kwargs)
        normalized = _normalize_links(result)
        if normalized:
            return normalized
    except Exception:
        pass

    base_url = (cfg.get("firecrawl_url") or "http://localhost:3002").rstrip("/")
    headers = {}
    api_key = cfg.get("firecrawl_api_key")
    if api_key and api_key != "local":
        headers["Authorization"] = f"Bearer {api_key}"
    for endpoint in ("/v2/map", "/v1/map", "/map"):
        try:
            response = requests.post(f"{base_url}{endpoint}", json=kwargs, headers=headers, timeout=20)
            response.raise_for_status()
            normalized = _normalize_links(response.json())
            if normalized:
                return normalized
        except requests.RequestException:
            continue
    return []


def _query_keywords(query: str) -> set[str]:
    return {token for token in query.lower().replace("/", " ").replace("-", " ").split() if len(token) > 2}


def _slug_match_score(url: str, keywords: set[str]) -> int:
    parsed = urlparse(url)
    haystack = f"{parsed.netloc} {parsed.path}".lower()
    return sum(1 for keyword in keywords if keyword in haystack)


def select_relevant_urls(query: str, mapped_links: list[dict[str, str]], limit: int = 8) -> list[str]:
    if not mapped_links:
        return []

    ordered_urls = [link["url"] for link in mapped_links if link.get("url")]
    if len(ordered_urls) >= limit and any(link.get("title") or link.get("description") for link in mapped_links):
        return ordered_urls[:limit]

    keywords = _query_keywords(query)
    scored = sorted(
        (
            (_slug_match_score(link["url"], keywords), index, link["url"])
            for index, link in enumerate(mapped_links)
            if link.get("url")
        ),
        key=lambda item: (-item[0], item[1]),
    )
    filtered = [url for score, _, url in scored if score > 0]
    if filtered:
        return filtered[:limit]
    return ordered_urls[:limit]


def map_and_filter(
    url: str,
    query: str,
    limit: int = 8,
    config: dict[str, Any] | None = None,
) -> tuple[list[dict[str, str]], list[str]]:
    links = map_links(url, query=query, max_results=max(100, limit * 10), config=config)
    return links, select_relevant_urls(query, links, limit=limit)
