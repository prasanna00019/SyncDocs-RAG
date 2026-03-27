from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any

DEFAULT_CONFIG: dict[str, Any] = {
    "firecrawl_url": "http://localhost:3002",
    "firecrawl_api_key": "local",
    "firecrawl_mode": "self_hosted",
    "ollama_chat_model": "",
    "embed_model": "sentence-transformers/all-MiniLM-L6-v2",
    "max_urls_to_scrape": 8,
    "scrape_max_age_ms": 3_600_000,
    "only_main_content": True,
    "last_active_library": "",
    "last_active_version": "latest",
    "indexed_sources": {},
}


def get_syncdocs_home() -> Path:
    override = os.getenv("SYNCDOCS_HOME")
    if override:
        return Path(override).expanduser().resolve()
    return (Path.home() / ".syncdocs").resolve()


def get_config_file() -> Path:
    return get_syncdocs_home() / "config.json"


def get_chroma_dir() -> Path:
    return get_syncdocs_home() / "chroma_db"


def get_bm25_dir() -> Path:
    return get_syncdocs_home() / "bm25"


def get_stack_dir() -> Path:
    return get_syncdocs_home() / "docker"


def ensure_runtime_dirs() -> None:
    home = get_syncdocs_home()
    home.mkdir(parents=True, exist_ok=True)
    get_chroma_dir().mkdir(parents=True, exist_ok=True)
    get_bm25_dir().mkdir(parents=True, exist_ok=True)


def _merge_defaults(raw: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(DEFAULT_CONFIG)
    merged.update(raw or {})
    merged["indexed_sources"] = {
        **DEFAULT_CONFIG["indexed_sources"],
        **(raw.get("indexed_sources", {}) if isinstance(raw, dict) else {}),
    }
    return merged


def load_config() -> dict[str, Any]:
    ensure_runtime_dirs()
    config_file = get_config_file()
    if not config_file.exists():
        config = deepcopy(DEFAULT_CONFIG)
        save_config(config)
        return config

    with config_file.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)
    return _merge_defaults(raw)


def save_config(config: dict[str, Any]) -> dict[str, Any]:
    ensure_runtime_dirs()
    merged = _merge_defaults(config)
    with get_config_file().open("w", encoding="utf-8") as handle:
        json.dump(merged, handle, indent=2, sort_keys=True)
    return merged
