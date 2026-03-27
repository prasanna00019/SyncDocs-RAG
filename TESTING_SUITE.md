# SyncDocs MCP Testing Suite

This guide is focused on testing the MCP server first. CLI and PyPI packaging validation can happen later.

## Recommended Test Order

Use this order:

1. MCP Inspector
2. Claude Desktop or Cursor

Why:

- MCP Inspector is the fastest way to verify that the server starts, tools register correctly, schemas look right, and each tool returns the shape you expect.
- A real MCP client should come second, after Inspector is green, to confirm end-to-end agent integration.

## What You Need Installed

Before testing, make sure you have:

- Python 3.10+
- `uv`
- Docker Desktop
- Ollama
- Node.js only if you want to use the Node-based MCP Inspector launcher

You also need this repo checked out locally.

## Services You Need Running

SyncDocs depends on:

- Ollama for chat generation
- Firecrawl for mapping and scraping
- SearXNG behind Firecrawl for web search
- ChromaDB and BM25 are local file-based storage, so there is no extra service to start for them

## First-Time Setup

### 1. Create the virtual environment and install the package

```bash
uv venv
uv pip install -e .
```

### 2. Make sure Ollama is running

Start Ollama in your normal way, then make sure you have at least one usable chat model.

A simple local option is:

```bash
ollama pull gemma3:4b
```

### 3. Start the local Firecrawl stack

Recommended:

```bash
syncdocs setup
```

If you want to start the stack manually later:

```bash
docker compose -f ~/.syncdocs/docker/docker-compose.yml up -d
```

### 4. Verify local services

Run:

```bash
syncdocs status
```

You want to see:

- Firecrawl reachable
- SearXNG reachable
- no critical config errors

If you want to verify manually outside the CLI:

```bash
curl http://localhost:3002
curl "http://localhost:8080/search?q=fastapi&format=json"
```

Expected result:

- Firecrawl responds from `/` with a small JSON payload
- SearXNG responds with search results JSON

## Start the MCP Server

Run this from the repo root:

```bash
python -m syncdocs_mcp
```

This starts the MCP server over stdio.

## Test In MCP Inspector

Use MCP Inspector first.

If you already have MCP Inspector installed, launch it with this server command:

- command: `python`
- args: `-m syncdocs_mcp`
- cwd: your repo root

If you use the Node-based Inspector launcher, one common way is:

```bash
npx @modelcontextprotocol/inspector python -m syncdocs_mcp
```

If your local Inspector setup expects a different launch flow, use the same command, args, and cwd shown above.

## Inspector Test Checklist

### Test 1: Server starts and tools are visible

Expected result:

- Inspector connects successfully
- these three tools appear:
  - `search_web`
  - `fetch_and_index`
  - `query_docs`

### Test 2: `search_web`

Call:

```json
{
  "query": "FastAPI dependency injection documentation",
  "limit": 5
}
```

Expected result:

- returns a list of ranked documentation candidates
- each item should include at least a URL

### Test 3: `fetch_and_index`

Call:

```json
{
  "url": "https://fastapi.tiangolo.com/",
  "library": "fastapi",
  "version": "latest",
  "query": "dependency injection with Depends"
}
```

Expected result:

- Firecrawl maps the site
- top URLs are selected
- pages are scraped
- changed/new pages are ingested
- response includes collection info and indexing counts

Good signs:

- `collection` is something like `fastapi_latest`
- `pages_indexed` is greater than `0` on first run
- `pages_skipped` may increase on later reruns because of change tracking

### Test 4: `query_docs`

Call:

```json
{
  "query": "How do I create reusable dependencies with Depends?",
  "library": "fastapi",
  "version": "latest"
}
```

Expected result:

- returns an answer grounded in the indexed docs
- includes `sources`
- answer should clearly relate to the indexed library and query

## Recommended Real Test Cases

Run these after the basic flow works.

### Case 1: FastAPI

- URL: `https://fastapi.tiangolo.com/`
- Library: `fastapi`
- Query for indexing: `dependency injection with Depends`
- Query for answering: `How do I create reusable dependencies with Depends?`

### Case 2: Stripe

- URL: `https://docs.stripe.com/`
- Library: `stripe`
- Query for indexing: `payment intents create confirm`
- Query for answering: `How do I confirm a PaymentIntent?`

### Case 3: LangChain

- URL: `https://python.langchain.com/docs/`
- Library: `langchain`
- Query for indexing: `retrieval chain document loaders`
- Query for answering: `How do I build a retrieval chain with documents?`

## Re-Run / Change Tracking Test

Run `fetch_and_index` twice with the same arguments.

Expected result:

- first run indexes pages
- second run should show more skipping if pages are unchanged

This is the easiest way to validate that the Firecrawl change-tracking path is active.

## Negative Tests

### Query before indexing

Call `query_docs` for a library you have not indexed yet.

Expected result:

- a clear error or failure indicating there is no indexed collection available yet

### Bad docs URL

Call `fetch_and_index` with an invalid docs URL.

Expected result:

- mapping or scraping should fail cleanly
- the server should not crash

### Ollama unavailable

Stop Ollama and call `query_docs`.

Expected result:

- you should get a model/runtime error instead of a silent failure

## What To Inspect On Disk

After a successful indexing run, check:

- `~/.syncdocs/config.json`
- `~/.syncdocs/chroma_db/`
- `~/.syncdocs/bm25/`

In `config.json`, confirm:

- `last_active_library`
- `last_active_version`
- `indexed_sources`

## Common Failure Points

### No tools appear in Inspector

Check:

- you launched `python -m syncdocs_mcp`
- the environment has the package installed with `uv pip install -e .`
- the `mcp` dependency is installed in the same environment

### `search_web` fails

Check:

- Firecrawl is reachable
- SearXNG is reachable
- `syncdocs status` reports both services correctly

### `fetch_and_index` fails

Check:

- Firecrawl stack is running
- the target docs site is reachable
- the docs URL is a real documentation root

### `query_docs` fails

Check:

- Ollama is running
- a chat model is available
- indexing completed successfully before querying

## Final Integration Check In A Real MCP Client

After Inspector passes:

1. Add SyncDocs to Claude Desktop or Cursor using:
   - command: `python`
   - args: `-m syncdocs_mcp`
   - cwd: repo root
2. Restart the client.
3. Confirm the tools are discovered.
4. Ask the client to:
   - search for docs
   - fetch and index a library
   - answer a question from those indexed docs

If Inspector works but the real client fails, the problem is usually client config rather than the MCP server logic itself.
