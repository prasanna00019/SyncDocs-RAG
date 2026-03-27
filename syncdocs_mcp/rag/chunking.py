from __future__ import annotations

import hashlib
import uuid
from typing import Any

HEADERS = [("#", "h1"), ("##", "h2"), ("###", "h3")]
PARENT_SIZE = 1500
PARENT_OVERLAP = 200
CHILD_SIZE = 400
CHILD_OVERLAP = 80


def compute_content_hash(markdown: str) -> str:
    return hashlib.sha256(markdown.encode("utf-8")).hexdigest()


def _document(page_content: str, metadata: dict[str, Any]):
    from langchain_core.documents import Document

    return Document(page_content=page_content, metadata=metadata)


def split_into_parent_child(markdown: str, source_url: str, content_hash: str):
    from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

    if not markdown.strip():
        return [], []

    header_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=HEADERS, strip_headers=False)
    header_splits = header_splitter.split_text(markdown)
    if not header_splits:
        header_splits = [_document(markdown, {})]

    parent_splitter = RecursiveCharacterTextSplitter(chunk_size=PARENT_SIZE, chunk_overlap=PARENT_OVERLAP)
    child_splitter = RecursiveCharacterTextSplitter(chunk_size=CHILD_SIZE, chunk_overlap=CHILD_OVERLAP)

    parents = []
    children = []

    for section in header_splits:
        section.metadata["source"] = source_url
        section.metadata["content_hash"] = content_hash
        parent_chunks = parent_splitter.split_documents([section])
        for parent in parent_chunks:
            parent_id = str(uuid.uuid4())
            parent.metadata["chunk_id"] = parent_id
            parent.metadata["chunk_type"] = "parent"
            parent.metadata["source"] = source_url
            parent.metadata["content_hash"] = content_hash
            parents.append(parent)

            for child in child_splitter.split_documents([parent]):
                child.metadata["chunk_id"] = str(uuid.uuid4())
                child.metadata["parent_id"] = parent_id
                child.metadata["chunk_type"] = "child"
                child.metadata["source"] = source_url
                child.metadata["content_hash"] = content_hash
                children.append(child)

    return parents, children
