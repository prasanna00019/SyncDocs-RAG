from __future__ import annotations

from functools import lru_cache


@lru_cache(maxsize=1)
def _cross_encoder():
    from sentence_transformers import CrossEncoder

    return CrossEncoder("cross-encoder/ms-marco-MiniLM-L6-v2")


def rerank(query: str, docs: list, top_k: int = 8) -> list:
    if len(docs) <= top_k:
        return docs
    try:
        encoder = _cross_encoder()
        scores = encoder.predict([(query, doc.page_content) for doc in docs])
        ranked = sorted(zip(scores, docs), key=lambda item: item[0], reverse=True)
        return [doc for _, doc in ranked[:top_k]]
    except Exception:
        return docs[:top_k]
