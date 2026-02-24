import os
import sys
import json
import asyncio
from typing import AsyncGenerator
from dotenv import load_dotenv

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from firecrawl_client import DocsCrawler
from url_filter import URLFilter
from rag_system import RAGSystem

load_dotenv()

app = FastAPI(title="Live Docs RAG API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Helpers ──────────────────────────────────────────────────────────

def _event(step: str, status: str, data=None):
    """Build a structured SSE payload."""
    return json.dumps({"step": step, "status": status, "data": data})


# ── Routes ───────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    from ollama_utils import get_best_ollama_model, get_embedding_model
    chat = get_best_ollama_model()
    embed = get_embedding_model()
    return {
        "status": "ok",
        "firecrawl_key_set": bool(os.getenv("FIRECRAWL_API_KEY")),
        "chat_model": chat,
        "embed_model": embed,
    }


@app.post("/api/rag")
async def rag_pipeline(request: Request):
    body = await request.json()
    url = body.get("url", "")
    query = body.get("query", "")
    limit = body.get("limit", 5)

    async def stream() -> AsyncGenerator[str, None]:
        # ── Security: Input Sanitization ────────────────────────
        if len(query) > 1000:
            yield _event("error", "done", {"message": "Query length exceeds security limit."})
            return
            
        blacklist = ["ignore all previous", "discard instructions", "system prompt", "jailbreak", "bypass"]
        query_lower = query.lower()
        if any(term in query_lower for term in blacklist):
            yield _event("error", "done", {"message": "Security Alert: Query contains prohibited phrases."})
            return

        try:
            # ── Step 0: Initialize ──────────────────────────────────
            yield _event("init", "running", {"message": "Initializing RAG pipeline..."})
            await asyncio.sleep(0)  # yield control

            crawler = DocsCrawler()
            url_filter = URLFilter()
            rag = RAGSystem()

            yield _event("init", "done", {
                "chat_model": rag.chat_model_name,
                "embed_model": rag.embed_model_name,
            })
            await asyncio.sleep(0)

            mapped_urls = []
            if url:
                # ── Step 1: Map ─────────────────────────────────────
                yield _event("map", "running", {"url": url})
                await asyncio.sleep(0)

                mapped_urls = await asyncio.to_thread(crawler.map_documentation, url)

                yield _event("map", "done", {
                    "total_links": len(mapped_urls),
                    "sample": mapped_urls[:10],
                })
                await asyncio.sleep(0)

                # ── Step 2: Filter ──────────────────────────────────
                yield _event("filter", "running", {
                    "query": query,
                    "total_urls": len(mapped_urls),
                })
                await asyncio.sleep(0)

                filtered = await asyncio.to_thread(url_filter.filter_urls, query, mapped_urls)
                urls_to_scrape = filtered[:limit]

                yield _event("filter", "done", {
                    "selected_urls": urls_to_scrape,
                    "count": len(urls_to_scrape),
                })
                await asyncio.sleep(0)

                if not urls_to_scrape:
                    yield _event("error", "done", {"message": "No relevant URLs found after filtering."})
                    return

                # ── Step 3: Scrape ──────────────────────────────────
                yield _event("scrape", "running", {"urls": urls_to_scrape})
                await asyncio.sleep(0)

                scraped_data = await asyncio.to_thread(crawler.scrape_urls, urls_to_scrape)

                yield _event("scrape", "done", {
                    "scraped_count": len(scraped_data),
                    "urls": [d["url"] for d in scraped_data],
                })
                await asyncio.sleep(0)

                if not scraped_data:
                    yield _event("error", "done", {"message": "Failed to scrape any content."})
                    return

                # ── Step 4: Chunk & Ingest ──────────────────────────
                yield _event("ingest", "running", {"doc_count": len(scraped_data)})
                await asyncio.sleep(0)

                await asyncio.to_thread(rag.chunk_and_ingest, scraped_data)

                yield _event("ingest", "done", {"message": "Chunks ingested into ChromaDB"})
                await asyncio.sleep(0)

            # ── Step 5: Generate Answer ─────────────────────────────
            yield _event("generate", "running", {"query": query})
            await asyncio.sleep(0)

            answer = await asyncio.to_thread(rag.query, query)

            yield _event("generate", "done", {"answer": answer})
            yield _event("complete", "done", {"message": "Pipeline complete"})

        except Exception as exc:
            yield _event("error", "done", {"message": str(exc)})

    return EventSourceResponse(stream(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
