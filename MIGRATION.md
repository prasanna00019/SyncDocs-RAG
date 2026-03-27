# syncdocs-mcp — Migration & Build Plan

> Migrating from: standalone FastAPI RAG server (SyncDocs RAG v1)  
> Migrating to: self-hosted MCP server package (`syncdocs-mcp`) with full local stack  
> Stack: Self-hosted Firecrawl + SearXNG (Docker) + ChromaDB + BM25 + Ollama

---

## Table of Contents

1. [Key Firecrawl API Insights](#key-firecrawl-api-insights)
2. [New Architecture Overview](#new-architecture-overview)
3. [What Changes, What Stays](#what-changes-what-stays)
4. [Project Structure](#project-structure)
5. [Phase 1 — Foundation & Firecrawl Refactor](#phase-1--foundation--firecrawl-refactor)
6. [Phase 2 — RAG Upgrades](#phase-2--rag-upgrades)
7. [Phase 3 — MCP Server](#phase-3--mcp-server)
8. [Phase 4 — CLI & Packaging](#phase-4--cli--packaging)
9. [Phase 5 — Polish & Release](#phase-5--polish--release)
10. [Docker Compose Stack](#docker-compose-stack)
11. [File-by-File Migration Map](#file-by-file-migration-map)
12. [Key Design Decisions](#key-design-decisions)

---

## Key Firecrawl API Insights

Before the plan, these are the specific API features that directly shape the new architecture:

### `/map` — has a built-in `search` param
```python
res = firecrawl.map(url="https://razorpay.com/docs", search="payment gateway setup js")
# Returns links ordered by relevance to the search term — no manual embedding needed
```
**Impact:** Our entire `url_filter.py` (HuggingFace embeddings on title+description) is **replaced** by this one parameter. The map endpoint already ranks URLs by semantic relevance internally. This removes a dependency and a significant chunk of computation.

### `/batch/scrape` — concurrent, not sequential
```python
job = firecrawl.batch_scrape(urls, formats=["markdown"], poll_interval=2)
```
**Impact:** Current `firecrawl_client.py` scrapes URLs one at a time in a `for` loop. Batch scrape processes all URLs concurrently. For 8 URLs, this is ~8x faster.

### `changeTracking` format — git-diff level, persistent, free
```python
result = firecrawl.scrape(url, formats=["markdown", {"type": "changeTracking", "modes": ["git-diff"], "tag": "razorpay_latest"}])
# changeStatus: "new" | "same" | "changed" | "removed"
# diff.text: actual unified diff of what changed line-by-line
```
**Impact:** On re-index calls, we only re-embed pages where `changeStatus == "changed"`. We get the actual diff so we can do surgical chunk updates instead of full re-embedding. Replaces our MD5 hash approach with something far more powerful. Tags let us track `{library}_v{version}` separately.

### `/map` returns `{url, title, description}` from sitemap
```python
# links: [{"url": "...", "title": "...", "description": "..."}]
```
**Impact:** Title and description are only present when the site has a proper sitemap.xml. For sites without one, we get raw URLs only. Need a URL-slug-based fallback filter for this case (keyword matching on path segments).

### `maxAge` for cache-backed fast scraping
```python
firecrawl.scrape(url, formats=["markdown"], max_age=3600000)  # 1 hour cache
```
**Impact:** For re-indexing runs where we just want to check for changes, set `max_age=3600000`. Firecrawl returns cached content instantly (500% faster) unless the page has been updated.

### `only_main_content=True` on scrape
Strips nav, footers, sidebars — gives much cleaner markdown for RAG. Always use this.

---

## New Architecture Overview

```
Developer's machine
├── Docker (managed by syncdocs setup)
│   ├── searxng:8080          ← web search
│   ├── firecrawl-api:3002    ← map + batch_scrape + change_tracking
│   ├── firecrawl-playwright  ← JS rendering for firecrawl
│   └── redis                 ← firecrawl job queue
│
└── syncdocs-mcp (Python process, stdio/SSE)
    ├── tool: search_web       → calls firecrawl /search (→ SearXNG)
    ├── tool: fetch_and_index  → map (search param) + batch_scrape (changeTracking) + RAG ingest
    ├── tool: query_docs       → HyDE + BM25+vector hybrid + rerank + LLM answer
    └── storage: ~/.syncdocs/chroma_db/   (versioned collections)
                ~/.syncdocs/bm25/         (BM25 index per collection)
                ~/.syncdocs/config.json
```

**Agent workflow (Razorpay example):**
```
Agent: "How to integrate Razorpay payment gateway in Next.js?"

1. search_web("Razorpay payment gateway Next.js integration")
   → [{url: "razorpay.com/docs", title: ...}, ...]

2. fetch_and_index(url="razorpay.com/docs", library="razorpay", version="latest")
   → map(url, search="payment gateway Next.js")  ← ranked URLs from Firecrawl
   → batch_scrape(top_8_urls, changeTracking, only_main_content=True)
   → ingest changed/new pages into collection "razorpay_latest"

3. query_docs("Razorpay payment gateway Next.js", library="razorpay")
   → HyDE → BM25+vector → RRF → parent chunks → cross-encoder → LLM
   → "Here's how to integrate Razorpay in Next.js: [answer with source URLs]"
```

---

## What Changes, What Stays

| Component | v1 (existing) | v2 (new) | Action |
|---|---|---|---|
| `url_filter.py` | HuggingFace embeddings on title+desc | `/map?search=query` native | **Delete** — replaced by map search param |
| `firecrawl_client.py` | Sequential scrape loop | `batch_scrape` + `changeTracking` | **Rewrite** |
| `rag_system.py` | Single ChromaDB collection, vector-only | Versioned collections, BM25+vector hybrid | **Major rewrite** |
| `server.py` | FastAPI + SSE + security blacklist | MCP server (stdio) + optional FastAPI SSE | **Replace** |
| `ollama_utils.py` | Chat + embed model picker | Same logic, keep as utility | **Keep, minor edits** |
| `compare_embeddings.py` | Benchmarking script | Not needed in production | **Archive** |
| `cross-encoder.py` | Test script | Extracted into `rag/reranker.py` | **Migrate** |
| `main.py` | Bare entrypoint | CLI entrypoint (`syncdocs setup`) | **Replace** |
| HuggingFace embeddings | `all-MiniLM-L6-v2` | Same — keep, it's fast and free | **Keep** |
| ChromaDB | `./chroma_db_v2` | `~/.syncdocs/chroma_db/` (global) | **Migrate path** |
| LangChain chains | `create_stuff_documents_chain` | Same — keep | **Keep** |
| HyDE | In `rag_system.py` | Extracted to `rag/hyde.py` | **Extract** |
| Cross-encoder | Inline in `rag_system.py` | Extracted to `rag/reranker.py` | **Extract** |

---

## Project Structure

```
syncdocs-mcp/                        ← Python package root
│
├── pyproject.toml                   ← package metadata, entry point: syncdocs
├── README.md
├── docker/
│   ├── docker-compose.yml           ← ships with package
│   └── searxng/
│       └── settings.yml             ← pre-configured (json output, good engines)
│
└── syncdocs_mcp/
    ├── __init__.py
    ├── __main__.py                  ← python -m syncdocs_mcp (starts MCP server)
    │
    ├── cli.py                       ← syncdocs setup | status | list | clear
    ├── config.py                    ← read/write ~/.syncdocs/config.json
    │
    ├── firecrawl/
    │   ├── __init__.py
    │   ├── client.py                ← Firecrawl(api_key="local", api_url="http://localhost:3002")
    │   ├── search.py                ← search_web() → /search via SearXNG
    │   ├── mapper.py                ← map_and_filter() using /map?search=query
    │   └── scraper.py               ← batch_scrape_with_change_tracking()
    │
    ├── rag/
    │   ├── __init__.py
    │   ├── chunking.py              ← parent-child splitter
    │   ├── hybrid.py                ← BM25 index (rank_bm25) + ChromaDB + RRF merge
    │   ├── hyde.py                  ← HyDE query expansion (extracted from rag_system.py)
    │   ├── reranker.py              ← cross-encoder reranker (extracted from rag_system.py)
    │   ├── versioning.py            ← collection naming: {library}_v{version}
    │   └── system.py                ← orchestrates all rag/ modules
    │
    └── server.py                    ← MCP server using `mcp` Python SDK (stdio transport)
```

---

## Phase 1 — Foundation & Firecrawl Refactor

**Goal:** Repo setup + replace v1 Firecrawl client with the new batch + change-tracking aware one. No RAG changes yet.

### Step 1.1 — Repo & package setup

```bash
mkdir syncdocs-mcp && cd syncdocs-mcp
uv init --package
uv add firecrawl-py mcp langchain-core langchain-community langchain-ollama \
        langchain-chroma sentence-transformers rank-bm25 \
        langchain-text-splitters chromadb python-dotenv rich click
```

`pyproject.toml` entry points:
```toml
[project.scripts]
syncdocs = "syncdocs_mcp.cli:main"
```

### Step 1.2 — Config module

`syncdocs_mcp/config.py`:
```python
CONFIG_DIR = Path.home() / ".syncdocs"
CONFIG_FILE = CONFIG_DIR / "config.json"
CHROMA_DIR = CONFIG_DIR / "chroma_db"
BM25_DIR = CONFIG_DIR / "bm25"

# Default config written by `syncdocs setup`
DEFAULT_CONFIG = {
    "firecrawl_url": "http://localhost:3002",
    "firecrawl_api_key": "local",        # no auth on self-hosted
    "ollama_chat_model": "",             # filled by setup
    "embed_model": "sentence-transformers/all-MiniLM-L6-v2",
    "max_urls_to_scrape": 8,
    "scrape_max_age_ms": 3600000,        # 1 hour cache for re-index runs
}
```

### Step 1.3 — New `firecrawl/client.py`

```python
from firecrawl import Firecrawl as _FC
from syncdocs_mcp.config import load_config

def get_client() -> _FC:
    cfg = load_config()
    return _FC(api_key=cfg["firecrawl_api_key"], api_url=cfg["firecrawl_url"])
```

### Step 1.4 — New `firecrawl/mapper.py`

**Key change:** drop `url_filter.py` entirely. Use `/map?search=query`.

```python
def map_and_filter(url: str, query: str, limit: int = 8) -> list[str]:
    """
    Maps a documentation site and returns URLs most relevant to `query`.
    Uses Firecrawl's built-in search ranking — no local embeddings needed.
    Falls back to slug-keyword matching if title/description are absent.
    """
    client = get_client()
    result = client.map(url=url, search=query, limit=100, sitemap="include")
    links = result.links if hasattr(result, "links") else result.get("links", [])

    # Firecrawl already ranked by relevance when search= is used
    # Just return the top N URLs
    urls = []
    for link in links:
        u = link.get("url") if isinstance(link, dict) else getattr(link, "url", str(link))
        if u:
            urls.append(u)

    # Fallback: if too few results (no sitemap), filter by query keywords in URL path
    if len(urls) < 3:
        keywords = set(query.lower().split())
        urls = [u for u in urls if any(kw in u.lower() for kw in keywords)] or urls

    return urls[:limit]
```

**Migration note:** Delete `url_filter.py` from the old project. Its entire role is handled here.

### Step 1.5 — New `firecrawl/scraper.py`

**Key changes:** use `batch_scrape` (not sequential loop) + `changeTracking`.

```python
def batch_scrape_with_change_tracking(
    urls: list[str],
    library: str,
    version: str,
    max_age_ms: int = 3600000
) -> list[dict]:
    """
    Batch scrapes URLs concurrently. Uses changeTracking to detect what's new/changed.
    Returns only pages that need re-indexing (new or changed).
    Unchanged pages return changeStatus="same" and are skipped.
    """
    client = get_client()
    tag = f"{library}_{version}"

    job = client.batch_scrape(
        urls,
        formats=[
            "markdown",
            {"type": "changeTracking", "modes": ["git-diff"], "tag": tag}
        ],
        only_main_content=True,
        poll_interval=2,
        wait_timeout=120
    )

    pages_to_ingest = []
    for page in job.data:
        ct = getattr(page, "changeTracking", None) or {}
        status = ct.get("changeStatus", "new") if isinstance(ct, dict) else getattr(ct, "changeStatus", "new")

        if status in ("new", "changed"):
            pages_to_ingest.append({
                "url": page.metadata.get("sourceURL", ""),
                "markdown": page.markdown or "",
                "change_status": status,
                "diff": ct.get("diff", {}) if isinstance(ct, dict) else getattr(ct, "diff", {}),
            })
        else:
            print(f"[scraper] Skipping unchanged page: {page.metadata.get('sourceURL', '')}")

    return pages_to_ingest
```

---

## Phase 2 — RAG Upgrades

**Goal:** Parent-child chunking, BM25 hybrid retrieval, versioned collections. These are independent of MCP and can be tested standalone.

### Step 2.1 — `rag/versioning.py`

```python
def collection_name(library: str, version: str) -> str:
    """
    Returns a safe ChromaDB collection name.
    e.g. "razorpay_latest", "langchain_v0_3", "fastapi_v0_115"
    """
    safe_version = version.replace(".", "_").replace("-", "_")
    return f"{library}_{safe_version}"

def list_collections() -> list[str]:
    ...

def delete_collection(library: str, version: str) -> None:
    ...
```

### Step 2.2 — `rag/chunking.py` — parent-child split

The idea: embed small child chunks (precise retrieval), store large parent chunks (rich context for LLM). Link them via metadata.

```python
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
import uuid

HEADERS = [("#", "h1"), ("##", "h2"), ("###", "h3")]
PARENT_SIZE = 1500   # chars — what the LLM sees
CHILD_SIZE  = 400    # chars — what gets embedded
CHILD_OVERLAP = 80

def split_into_parent_child(markdown: str, source_url: str, content_hash: str) -> tuple[list, list]:
    """
    Returns (parent_docs, child_docs).
    Each child_doc.metadata contains parent_id to look up the parent.
    """
    md_splitter = MarkdownHeaderTextSplitter(HEADERS, strip_headers=False)
    header_splits = md_splitter.split_text(markdown)

    parent_splitter = RecursiveCharacterTextSplitter(chunk_size=PARENT_SIZE, chunk_overlap=200)
    child_splitter  = RecursiveCharacterTextSplitter(chunk_size=CHILD_SIZE,  chunk_overlap=CHILD_OVERLAP)

    parents, children = [], []

    for section in header_splits:
        section.metadata["source"] = source_url
        section.metadata["content_hash"] = content_hash
        parent_chunks = parent_splitter.split_documents([section])

        for parent in parent_chunks:
            parent_id = str(uuid.uuid4())
            parent.metadata["chunk_id"] = parent_id
            parent.metadata["chunk_type"] = "parent"
            parents.append(parent)

            child_chunks = child_splitter.split_documents([parent])
            for child in child_chunks:
                child.metadata["parent_id"] = parent_id
                child.metadata["chunk_type"] = "child"
                children.append(child)

    return parents, children
```

### Step 2.3 — `rag/hybrid.py` — BM25 + ChromaDB + RRF

Two separate stores per collection:
- ChromaDB: stores **child chunks** (small, precise embeddings)
- BM25 index: built from child chunk text, persisted as pickle to `~/.syncdocs/bm25/{collection}.pkl`

```python
from rank_bm25 import BM25Okapi
import pickle, re

def build_bm25_index(docs: list, collection_name: str) -> None:
    tokenized = [_tokenize(d.page_content) for d in docs]
    index = BM25Okapi(tokenized)
    path = BM25_DIR / f"{collection_name}.pkl"
    with open(path, "wb") as f:
        pickle.dump({"index": index, "docs": docs}, f)

def hybrid_search(query: str, collection_name: str, k: int = 25) -> list:
    """
    Runs BM25 and vector search in parallel, merges with Reciprocal Rank Fusion.
    Returns top-k child docs.
    """
    bm25_results  = _bm25_search(query, collection_name, k)
    vector_results = _vector_search(query, collection_name, k)
    return _rrf_merge(bm25_results, vector_results, k)

def _rrf_merge(list_a, list_b, k, rrf_k=60) -> list:
    scores = {}
    for rank, doc in enumerate(list_a):
        key = doc.metadata.get("chunk_id", doc.page_content[:50])
        scores[key] = scores.get(key, 0) + 1 / (rrf_k + rank + 1)
    for rank, doc in enumerate(list_b):
        key = doc.metadata.get("chunk_id", doc.page_content[:50])
        scores[key] = scores.get(key, 0) + 1 / (rrf_k + rank + 1)
    # Re-sort by merged score, return top k docs
    ...
```

### Step 2.4 — `rag/hyde.py`

Extract HyDE from `rag_system.py` verbatim, just clean it up:

```python
def generate_hyde_query(user_query: str, llm) -> str:
    """Generates a hypothetical answer and appends to original query for better retrieval."""
    ...
```

### Step 2.5 — `rag/reranker.py`

Extract cross-encoder from `rag_system.py` verbatim:

```python
def rerank(query: str, docs: list, top_k: int = 8) -> list:
    """Cross-encoder reranker using ms-marco-MiniLM-L6-v2."""
    ...
```

### Step 2.6 — `rag/system.py` — full orchestration

```python
class RAGSystem:
    def ingest(self, pages: list[dict], library: str, version: str) -> None:
        """
        Takes output of batch_scrape_with_change_tracking().
        Only receives new/changed pages — unchanged pages already skipped upstream.
        """
        coll = collection_name(library, version)
        for page in pages:
            parents, children = split_into_parent_child(
                page["markdown"], page["url"], page.get("content_hash", "")
            )
            # Store parents in a separate "parents" collection (for context expansion)
            # Store children in main collection (for embedding search)
            self.vectorstore_children.add_documents(children)
            self.vectorstore_parents.add_documents(parents)
        # Rebuild BM25 from all children (incremental update not supported by rank_bm25)
        all_children = self._get_all_children(coll)
        build_bm25_index(all_children, coll)

    def query(self, user_query: str, library: str, version: str) -> dict:
        coll = collection_name(library, version)
        # 1. HyDE
        search_query = generate_hyde_query(user_query, self.llm)
        # 2. Hybrid retrieve children
        child_docs = hybrid_search(search_query, coll, k=25)
        # 3. Expand to parents
        parent_docs = self._expand_to_parents(child_docs, coll)
        # 4. Rerank parents
        final_docs = rerank(user_query, parent_docs, top_k=8)
        # 5. LLM answer
        answer = self._generate_answer(user_query, final_docs)
        return {"answer": answer, "sources": list({d.metadata["source"] for d in final_docs})}
```

**Migration note:** The old `rag_system.py` is fully replaced by `rag/system.py` + the extracted modules above.

---

## Phase 3 — MCP Server

**Goal:** Wire the 3 MCP tools using the `mcp` Python SDK. Test in Claude Desktop.

### Step 3.1 — Install MCP SDK

```bash
uv add mcp
```

### Step 3.2 — `server.py` — 3 tools

```python
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

server = Server("syncdocs-mcp")
rag = RAGSystem()

@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="search_web",
            description="Search the web for documentation links. Returns ranked URLs with titles and descriptions. Use this first to find the docs URL for a library.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query, e.g. 'Razorpay payment gateway Next.js integration'"},
                    "limit": {"type": "integer", "default": 5}
                },
                "required": ["query"]
            }
        ),
        types.Tool(
            name="fetch_and_index",
            description="Fetches and indexes documentation from a URL into the local knowledge base. Automatically skips pages that haven't changed since last index. Call this before query_docs.",
            inputSchema={
                "type": "object",
                "properties": {
                    "url":     {"type": "string",  "description": "Root documentation URL, e.g. 'https://razorpay.com/docs/'"},
                    "library": {"type": "string",  "description": "Library name, e.g. 'razorpay'"},
                    "version": {"type": "string",  "description": "Version string, e.g. 'latest' or '0.3'", "default": "latest"},
                    "query":   {"type": "string",  "description": "The coding question — used to select the most relevant pages to index"}
                },
                "required": ["url", "library", "query"]
            }
        ),
        types.Tool(
            name="query_docs",
            description="Queries the indexed documentation for a library and returns a grounded, cited answer. Must call fetch_and_index first for any new library.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query":   {"type": "string"},
                    "library": {"type": "string"},
                    "version": {"type": "string", "default": "latest"}
                },
                "required": ["query", "library"]
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "search_web":
        results = await asyncio.to_thread(search_web, arguments["query"], arguments.get("limit", 5))
        return [types.TextContent(type="text", text=json.dumps(results, indent=2))]

    elif name == "fetch_and_index":
        urls = map_and_filter(arguments["url"], arguments["query"], limit=cfg["max_urls_to_scrape"])
        pages = batch_scrape_with_change_tracking(urls, arguments["library"], arguments.get("version", "latest"))
        rag.ingest(pages, arguments["library"], arguments.get("version", "latest"))
        return [types.TextContent(type="text", text=f"Indexed {len(pages)} new/changed pages. Collection: {collection_name(arguments['library'], arguments.get('version', 'latest'))}")]

    elif name == "query_docs":
        result = await asyncio.to_thread(rag.query, arguments["query"], arguments["library"], arguments.get("version", "latest"))
        return [types.TextContent(type="text", text=result["answer"] + "\n\nSources:\n" + "\n".join(result["sources"]))]

async def main():
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())
```

### Step 3.3 — Test in Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "syncdocs": {
      "command": "python",
      "args": ["-m", "syncdocs_mcp"],
      "cwd": "/path/to/syncdocs-mcp"
    }
  }
}
```

---

## Phase 4 — CLI & Packaging

**Goal:** `syncdocs setup` makes the entire stack zero-config for a new developer.

### Step 4.1 — `cli.py`

```python
import click, subprocess, time, requests
from rich.console import Console

@click.group()
def main(): pass

@main.command()
def setup():
    """Interactive setup: starts Docker stack, configures Ollama model, writes config."""
    console = Console()
    console.print("[bold green]syncdocs-mcp setup[/bold green]")

    # 1. Check Docker
    # 2. Copy docker-compose.yml to ~/.syncdocs/
    # 3. docker compose up -d
    # 4. Wait for health (poll http://localhost:3002/health and http://localhost:8080)
    # 5. List Ollama models → prompt user to pick chat model
    # 6. Write ~/.syncdocs/config.json
    # 7. Print MCP config snippet for Claude Desktop + Cursor

@main.command()
def status():
    """Show status of Docker services and indexed collections."""
    ...

@main.command()
def list_collections():
    """List all indexed library collections with page counts."""
    ...

@main.command()
@click.argument("library")
@click.argument("version", default="latest")
def clear(library, version):
    """Delete a specific library collection from the index."""
    ...
```

### Step 4.2 — `pyproject.toml`

```toml
[project]
name = "syncdocs-mcp"
version = "0.1.0"
description = "Self-hosted MCP server for live documentation RAG. Works with Claude Desktop, Cursor, and any MCP-compatible agent."
requires-python = ">=3.10"
dependencies = [
    "firecrawl-py>=1.0",
    "mcp>=1.0",
    "langchain-core",
    "langchain-community",
    "langchain-ollama",
    "langchain-chroma",
    "langchain-text-splitters",
    "sentence-transformers",
    "rank-bm25",
    "chromadb",
    "python-dotenv",
    "rich",
    "click",
]

[project.scripts]
syncdocs = "syncdocs_mcp.cli:main"
```

---

## Phase 5 — Polish & Release

- [ ] Add `syncdocs refresh <library> <version>` — re-indexes entire collection, uses changeTracking to skip unchanged
- [ ] Add `only_main_content` as a configurable option (default: True)
- [ ] Add collection stats to `syncdocs status` (page count, last indexed, changed pages on last run)
- [ ] Write README with quickstart (5 commands from install to first query)
- [ ] Test with: Razorpay, LangChain, FastAPI, Stripe, Supabase
- [ ] Publish to PyPI: `uv publish`
- [ ] Optional: keep the original FastAPI SSE frontend as a `syncdocs ui` command

---

## Docker Compose Stack

Save this at `docker/docker-compose.yml`:

```yaml
version: "3.8"

services:
  redis:
    image: redis:7-alpine
    restart: unless-stopped

  searxng:
    image: searxng/searxng:latest
    restart: unless-stopped
    ports:
      - "8080:8080"
    volumes:
      - ./searxng:/etc/searxng:rw
    environment:
      - SEARXNG_BASE_URL=http://localhost:8080/

  playwright:
    image: ghcr.io/browserless/chromium:latest
    restart: unless-stopped
    environment:
      - TIMEOUT=30000
      - CONCURRENT=10

  firecrawl:
    image: ghcr.io/firecrawl/firecrawl:latest
    restart: unless-stopped
    ports:
      - "3002:3002"
    depends_on:
      - redis
      - searxng
      - playwright
    environment:
      - REDIS_URL=redis://redis:6379
      - PLAYWRIGHT_MICROSERVICE_URL=http://playwright:3000
      - SEARXNG_ENDPOINT=http://searxng:8080
      - USE_DB_AUTHENTICATION=false
      - PORT=3002
```

Save this at `docker/searxng/settings.yml`:
```yaml
use_default_settings: true

search:
  formats:
    - html
    - json          # Required for Firecrawl to consume SearXNG results

engines:
  - name: google
    engine: google
    weight: 2
  - name: duckduckgo
    engine: duckduckgo
    weight: 1
  - name: bing
    engine: bing
    weight: 1

server:
  limiter: false    # Disable rate limiting for local use
```

---

## File-by-File Migration Map

```
OLD FILE                  →  NEW LOCATION / ACTION
─────────────────────────────────────────────────────────────────
server.py                 →  DELETE (replaced by syncdocs_mcp/server.py — MCP)
url_filter.py             →  DELETE (replaced by firecrawl/mapper.py — /map?search=)
rag_system.py             →  SPLIT into rag/system.py + rag/chunking.py + rag/hybrid.py +
                              rag/hyde.py + rag/reranker.py
firecrawl_client.py       →  REWRITE as firecrawl/client.py + firecrawl/scraper.py
ollama_utils.py           →  KEEP → syncdocs_mcp/ollama_utils.py (minor path update)
main.py                   →  REPLACE with syncdocs_mcp/cli.py
compare_embeddings.py     →  ARCHIVE (was a benchmark, not production code)
cross-encoder.py          →  ARCHIVE (logic moved into rag/reranker.py)
.env                      →  REPLACE with ~/.syncdocs/config.json (managed by CLI)
chroma_db_v2/             →  MIGRATE to ~/.syncdocs/chroma_db/ (or start fresh)
requirements.txt          →  REPLACE with pyproject.toml dependencies
```

---

## Key Design Decisions

**Why delete `url_filter.py` entirely?**
The `/map?search=query` parameter in Firecrawl v2 already ranks URLs by semantic relevance to the query. It uses the same signal (title + description) that our embedding filter used, but runs server-side and requires zero local computation. One less model to load, one less dependency, faster.

**Why `batch_scrape` over sequential?**
The old client scraped N URLs in a for-loop, each taking 2-5 seconds. `batch_scrape` submits all at once and Firecrawl processes them concurrently using its own worker pool. For 8 URLs, sequential = ~30 seconds. Batch = ~5 seconds.

**Why `changeTracking` with `git-diff` mode?**
The old MD5 hash approach skipped re-embedding unchanged pages (good) but couldn't do partial updates (if 1 sentence changed, re-embed the whole page). With git-diff we get the exact lines changed. In a future v2, we can use this diff to surgically update only the affected chunks rather than the whole page.

**Why version in the ChromaDB collection name?**
An agent coding against LangChain v0.2 and LangChain v0.3 simultaneously needs different answers. If both versions land in the same collection, vector search blends them and produces incorrect or contradictory answers. `{library}_v{version}` collections keep them isolated.

**Why not store parents in ChromaDB too?**
We store parents in a separate ChromaDB collection (`{coll}_parents`) keyed by `chunk_id`. On query, we retrieve child chunks (small, precise), look up their `parent_id`, fetch the parent text, and pass the larger parent context to the LLM. This is standard "small-to-big" RAG — retrieval precision stays high, but the LLM sees enough context to give a complete answer.

**Why keep HuggingFace embeddings (MiniLM) instead of Ollama?**
The `compare_embeddings.py` benchmark in the existing project already found that MiniLM is ~17x faster than Ollama embedding models for local inference. Since embedding is on the hot path (every chunk on every ingest), this matters. MiniLM runs on CPU, loads once, and is more than accurate enough for RAG retrieval.
