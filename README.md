# SyncDocs MCP

SyncDocs MCP is a local-first documentation RAG stack that now lives as a root Python package, with:

- an MCP server for Claude Desktop, Cursor, and other MCP clients
- a shared service layer for indexing and querying docs
- a compatibility FastAPI backend so the existing frontend still works
- Docker assets for a self-hosted Firecrawl + SearXNG stack

## Current Architecture

The project is no longer centered on the old standalone `backend/` app. The main runtime now lives in:

```text
syncdocs_mcp/
  cli.py
  config.py
  server.py
  service.py
  firecrawl/
  rag/
docker/
backend/
frontend/
tests/
```

Key changes in this migration:

- Firecrawl mapping now uses `/map?search=` instead of local URL embedding filtering
- scraping now uses `batch_scrape` plus `changeTracking`
- retrieval now uses parent/child chunking, BM25 + vector hybrid search, HyDE, and reranking
- runtime state moved to `~/.syncdocs/`
- `backend/` now acts as a compatibility wrapper over the new package

## Install

```bash
uv venv
uv pip install -e .
```

## Local Setup

Run:

```bash
syncdocs setup
```

That will:

- create `~/.syncdocs/config.json`
- copy the bundled Docker assets into `~/.syncdocs/docker`
- optionally start the local Docker stack
- store the chosen Ollama chat model in config
- start an upstream-aligned Firecrawl self-host stack with:
  - `firecrawl`
  - `playwright-service`
  - `nuq-postgres`
  - `rabbitmq`
  - `redis`
  - `searxng`

Runtime state lives in:

- `~/.syncdocs/config.json`
- `~/.syncdocs/chroma_db/`
- `~/.syncdocs/bm25/`
- `~/.syncdocs/docker/`

## MCP Server

Start the MCP server with:

```bash
python -m syncdocs_mcp
```

Exposed MCP tools:

- `search_web(query, limit=5)`
- `fetch_and_index(url, library, query, version="latest")`
- `query_docs(query, library, version="latest")`

### MCP Client Config

Example config for Claude Desktop or Cursor:

```json
{
  "mcpServers": {
    "syncdocs": {
      "command": "python",
      "args": ["-m", "syncdocs_mcp"],
      "cwd": "C:/path/to/SyncDocs-RAG"
    }
  }
}
```

## Recommended Testing Path

Test the MCP server in this order:

1. MCP Inspector first, because it gives you direct visibility into the tool list, raw inputs, and raw outputs.
2. Claude Desktop or Cursor second, as a final integration check with a real agent client.

The full setup and step-by-step test flow is documented in [TESTING_SUITE.md](./TESTING_SUITE.md).

For a quick manual reachability check after startup:

```bash
curl http://localhost:3002
curl http://localhost:8080
```

Expected:

- Firecrawl returns a small JSON response like `{"message":"Firecrawl API", ...}`
- SearXNG returns HTML on `/` and JSON on `/search?...&format=json`

## CLI

Available commands:

```bash
syncdocs setup
syncdocs status
syncdocs list
syncdocs clear stripe latest
syncdocs refresh stripe latest
```

## Demo Compatibility Mode

The existing frontend is still supported.

### Backend

```bash
cd backend
uv pip install -r requirements.txt
python server.py
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The compatibility backend keeps:

- `GET /api/health`
- `POST /api/rag`

When a URL is provided in the demo, SyncDocs infers a library name from the domain, indexes it as `latest`, and stores it as the active collection for follow-up queries.

## Verification

Current repo-level verification:

```bash
python -m compileall syncdocs_mcp backend tests
python -m unittest discover -s tests
```
