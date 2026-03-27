from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from syncdocs_mcp.config import get_bm25_dir, get_chroma_dir

SAFE_NAME_RE = re.compile(r"[^a-z0-9_]+")


def sanitize_identifier(value: str) -> str:
    cleaned = SAFE_NAME_RE.sub("_", value.strip().lower())
    return cleaned.strip("_") or "docs"


def collection_name(library: str, version: str = "latest") -> str:
    return f"{sanitize_identifier(library)}_{sanitize_identifier(version)}"


def parents_collection_name(name: str) -> str:
    return f"{name}_parents"


def _client(chroma_dir: str | None = None):
    import chromadb

    return chromadb.PersistentClient(path=chroma_dir or str(get_chroma_dir()))


def list_collections(chroma_dir: str | None = None) -> list[str]:
    client = _client(chroma_dir)
    return sorted(
        collection.name
        for collection in client.list_collections()
        if not collection.name.endswith("_parents")
    )


def collection_stats(name: str, chroma_dir: str | None = None) -> dict[str, Any]:
    client = _client(chroma_dir)
    collection = client.get_collection(name=name)
    parent_name = parents_collection_name(name)
    parent_count = 0
    try:
        parent_count = client.get_collection(name=parent_name).count()
    except Exception:
        parent_count = 0
    return {"name": name, "child_count": collection.count(), "parent_count": parent_count}


def list_collection_details(chroma_dir: str | None = None) -> list[dict[str, Any]]:
    details = []
    for name in list_collections(chroma_dir=chroma_dir):
        try:
            details.append(collection_stats(name, chroma_dir=chroma_dir))
        except Exception:
            details.append({"name": name, "child_count": 0, "parent_count": 0})
    return details


def delete_collection(library: str, version: str = "latest", chroma_dir: str | None = None, bm25_dir: str | None = None) -> None:
    name = collection_name(library, version)
    client = _client(chroma_dir)
    for target in (name, parents_collection_name(name)):
        try:
            client.delete_collection(target)
        except Exception:
            pass

    bm25_path = Path(bm25_dir or str(get_bm25_dir())) / f"{name}.pkl"
    if bm25_path.exists():
        bm25_path.unlink()
