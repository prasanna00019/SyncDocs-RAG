from __future__ import annotations

import pickle
import re
from pathlib import Path
from typing import Any

from syncdocs_mcp.config import get_bm25_dir, get_chroma_dir

TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_]+")


def _tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_PATTERN.findall(text)]


def _serialize_doc(doc: Any) -> dict[str, Any]:
    return {"page_content": doc.page_content, "metadata": dict(doc.metadata)}


def _deserialize_doc(payload: dict[str, Any]):
    from langchain_core.documents import Document

    return Document(page_content=payload["page_content"], metadata=payload.get("metadata", {}))


def _bm25_path(collection_name: str, base_dir: Path | None = None) -> Path:
    root = base_dir or get_bm25_dir()
    root.mkdir(parents=True, exist_ok=True)
    return root / f"{collection_name}.pkl"


def build_bm25_index(docs: list, collection_name: str, base_dir: Path | None = None) -> Path:
    payload = {
        "tokenized": [_tokenize(doc.page_content) for doc in docs],
        "docs": [_serialize_doc(doc) for doc in docs],
    }
    path = _bm25_path(collection_name, base_dir)
    with path.open("wb") as handle:
        pickle.dump(payload, handle)
    return path


def load_bm25_bundle(collection_name: str, base_dir: Path | None = None) -> dict[str, Any]:
    path = _bm25_path(collection_name, base_dir)
    if not path.exists():
        return {"tokenized": [], "docs": []}
    with path.open("rb") as handle:
        return pickle.load(handle)


def _bm25_search(query: str, collection_name: str, k: int = 25, base_dir: Path | None = None) -> list:
    from rank_bm25 import BM25Okapi

    bundle = load_bm25_bundle(collection_name, base_dir=base_dir)
    tokenized_docs = bundle.get("tokenized", [])
    docs = [_deserialize_doc(item) for item in bundle.get("docs", [])]
    if not tokenized_docs or not docs:
        return []
    bm25 = BM25Okapi(tokenized_docs)
    scores = bm25.get_scores(_tokenize(query))
    ranked_indices = sorted(range(len(scores)), key=lambda index: scores[index], reverse=True)
    return [docs[index] for index in ranked_indices[:k] if scores[index] > 0]


def _vector_search(query: str, collection_name: str, embeddings, k: int = 25, persist_directory: str | None = None) -> list:
    from langchain_chroma import Chroma

    store = Chroma(
        collection_name=collection_name,
        embedding_function=embeddings,
        persist_directory=persist_directory or str(get_chroma_dir()),
    )
    retriever = store.as_retriever(search_type="similarity", search_kwargs={"k": k})
    return retriever.invoke(query)


def _doc_key(doc: Any) -> str:
    metadata = getattr(doc, "metadata", {}) or {}
    return metadata.get("chunk_id") or metadata.get("parent_id") or doc.page_content[:80]


def _rrf_merge(list_a: list, list_b: list, k: int, rrf_k: int = 60) -> list:
    scores: dict[str, float] = {}
    doc_map: dict[str, Any] = {}

    for rank, doc in enumerate(list_a):
        key = _doc_key(doc)
        scores[key] = scores.get(key, 0.0) + 1.0 / (rrf_k + rank + 1)
        doc_map[key] = doc

    for rank, doc in enumerate(list_b):
        key = _doc_key(doc)
        scores[key] = scores.get(key, 0.0) + 1.0 / (rrf_k + rank + 1)
        doc_map[key] = doc

    ranked_keys = sorted(scores, key=lambda key: scores[key], reverse=True)
    return [doc_map[key] for key in ranked_keys[:k]]


def hybrid_search(
    query: str,
    collection_name: str,
    embeddings,
    k: int = 25,
    persist_directory: str | None = None,
    bm25_dir: Path | None = None,
) -> list:
    bm25_results = _bm25_search(query, collection_name, k=k, base_dir=bm25_dir)
    vector_results = _vector_search(query, collection_name, embeddings, k=k, persist_directory=persist_directory)
    return _rrf_merge(bm25_results, vector_results, k)
