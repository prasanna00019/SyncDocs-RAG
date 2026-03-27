from __future__ import annotations

from typing import Any

from syncdocs_mcp.config import load_config


def get_client(config: dict[str, Any] | None = None) -> Any:
    cfg = config or load_config()
    from firecrawl import Firecrawl as FirecrawlClient

    return FirecrawlClient(
        api_key=cfg.get("firecrawl_api_key") or "local",
        api_url=cfg.get("firecrawl_url") or "http://localhost:3002",
    )
