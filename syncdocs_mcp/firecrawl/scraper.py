from __future__ import annotations

import time
from typing import Any
from urllib.parse import urljoin

import requests

from syncdocs_mcp.config import load_config
from syncdocs_mcp.rag.chunking import compute_content_hash


def _to_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if value is None:
        return {}
    return {
        key: getattr(value, key)
        for key in dir(value)
        if not key.startswith("_") and not callable(getattr(value, key))
    }


def _extract_pages(payload: Any) -> list[Any]:
    if isinstance(payload, dict):
        return payload.get("data", [])
    return getattr(payload, "data", [])


def _headers(config: dict[str, Any]) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    api_key = config.get("firecrawl_api_key")
    if api_key and api_key != "local":
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def _base_url(config: dict[str, Any]) -> str:
    return (config.get("firecrawl_url") or "http://localhost:3002").rstrip("/")


def _post_batch_job(
    urls: list[str],
    formats: list[Any],
    config: dict[str, Any],
    max_age_ms: int,
) -> dict[str, Any]:
    payload = {
        "urls": urls,
        "formats": formats,
        "onlyMainContent": bool(config.get("only_main_content", True)),
        "maxAge": max_age_ms,
    }
    headers = _headers(config)
    last_error: Exception | None = None
    for endpoint in ("/v2/batch/scrape", "/v1/batch/scrape", "/batch/scrape"):
        try:
            response = requests.post(
                f"{_base_url(config)}{endpoint}",
                json=payload,
                headers=headers,
                timeout=30,
            )
            response.raise_for_status()
            body = response.json()
            if isinstance(body, dict):
                return body
        except requests.RequestException as exc:
            last_error = exc
            continue
    raise RuntimeError(f"Firecrawl batch scrape request failed: {last_error}")


def _collect_paginated_pages(payload: dict[str, Any], headers: dict[str, str]) -> list[Any]:
    pages = list(_extract_pages(payload))
    next_url = payload.get("next")
    visited: set[str] = set()
    while next_url and next_url not in visited:
        visited.add(next_url)
        try:
            response = requests.get(next_url, headers=headers, timeout=30)
            response.raise_for_status()
        except requests.RequestException:
            break
        next_payload = response.json()
        pages.extend(_extract_pages(next_payload))
        next_url = next_payload.get("next")
    return pages


def _poll_batch_job(
    job: dict[str, Any],
    config: dict[str, Any],
    poll_interval: int = 2,
    wait_timeout: int = 120,
) -> dict[str, Any]:
    if _extract_pages(job):
        return job

    poll_url = job.get("url")
    if not poll_url and job.get("id"):
        poll_url = urljoin(f"{_base_url(config)}/", f"v2/batch/scrape/{job['id']}")
    if not poll_url:
        return job

    headers = _headers(config)
    deadline = time.time() + wait_timeout
    last_payload = job
    best_payload = job if _extract_pages(job) else None
    while time.time() < deadline:
        try:
            response = requests.get(poll_url, headers=headers, timeout=30)
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException:
            time.sleep(poll_interval)
            continue

        last_payload = payload if isinstance(payload, dict) else last_payload
        pages = _extract_pages(last_payload)
        if pages:
            best_payload = dict(last_payload)
        status = str(last_payload.get("status", "")).lower()
        completed = int(last_payload.get("completed") or 0)
        total = int(last_payload.get("total") or 0)
        has_terminal_status = status in {"completed", "failed", "cancelled", "canceled"}
        if pages and (has_terminal_status or (total > 0 and completed >= total)):
            ready_payload = dict(last_payload)
            ready_payload["data"] = _collect_paginated_pages(ready_payload, headers)
            return ready_payload
        if has_terminal_status:
            if best_payload and _extract_pages(best_payload):
                ready_payload = dict(best_payload)
                ready_payload["status"] = status or ready_payload.get("status", "")
                ready_payload["completed"] = completed or ready_payload.get("completed", 0)
                ready_payload["total"] = total or ready_payload.get("total", 0)
                ready_payload["data"] = _collect_paginated_pages(ready_payload, headers)
                return ready_payload
            return last_payload
        time.sleep(poll_interval)
    if best_payload and _extract_pages(best_payload):
        ready_payload = dict(best_payload)
        ready_payload["data"] = _collect_paginated_pages(ready_payload, headers)
        return ready_payload
    return last_payload


def _normalize_change_tracking(page_dict: dict[str, Any]) -> dict[str, Any]:
    return _to_dict(
        page_dict.get("changeTracking")
        or page_dict.get("change_tracking")
        or page_dict.get("change_tracking_data")
    )


def batch_scrape_with_change_tracking(
    urls: list[str],
    library: str,
    version: str,
    max_age_ms: int | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cfg = config or load_config()
    if not urls:
        return {"pages": [], "skipped": 0, "total": 0}

    tag = f"{library}_{version}"
    effective_max_age = max_age_ms if max_age_ms is not None else cfg.get("scrape_max_age_ms", 3_600_000)
    formats = [
        "markdown",
        {"type": "changeTracking", "modes": ["git-diff"], "tag": tag},
    ]
    job = _post_batch_job(urls, formats, cfg, int(effective_max_age))
    result = _poll_batch_job(job, cfg, poll_interval=2, wait_timeout=120)
    used_fallback = False
    if not _extract_pages(result):
        fallback_job = _post_batch_job(urls, ["markdown"], cfg, int(effective_max_age))
        fallback_result = _poll_batch_job(fallback_job, cfg, poll_interval=2, wait_timeout=120)
        if _extract_pages(fallback_result):
            result = fallback_result
            used_fallback = True

    pages_to_ingest: list[dict[str, Any]] = []
    skipped = 0
    returned_urls: set[str] = set()
    for page in _extract_pages(result):
        page_dict = _to_dict(page)
        metadata = _to_dict(getattr(page, "metadata", None) or page_dict.get("metadata"))
        change_tracking = _normalize_change_tracking(page_dict)
        status = change_tracking.get("changeStatus", "new")
        markdown = getattr(page, "markdown", None) or page_dict.get("markdown") or ""
        source_url = metadata.get("sourceURL") or metadata.get("url") or getattr(page, "url", "") or ""
        if source_url:
            returned_urls.add(source_url)

        if status in {"new", "changed"}:
            pages_to_ingest.append(
                {
                    "url": source_url,
                    "markdown": markdown,
                    "metadata": metadata,
                    "change_status": status,
                    "diff": change_tracking.get("diff", {}),
                    "content_hash": compute_content_hash(markdown),
                }
            )
        else:
            skipped += 1

    missing_urls = [url for url in urls if url not in returned_urls]
    warning = ""
    if not pages_to_ingest:
        warning = (
            "Firecrawl returned no indexable page content. "
            "On self-hosted mode this usually means the target blocked scraping, returned 403, or all pages were unchanged."
        )
    elif used_fallback:
        warning = (
            "Firecrawl self-hosted returned empty results for changeTracking, so SyncDocs retried with markdown-only scraping."
        )

    return {
        "pages": pages_to_ingest,
        "skipped": skipped,
        "total": len(urls),
        "job_status": result.get("status", ""),
        "completed": int(result.get("completed") or 0),
        "returned_pages": len(_extract_pages(result)),
        "missing_urls": missing_urls,
        "warning": warning,
    }
