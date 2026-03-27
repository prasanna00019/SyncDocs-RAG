import json
import asyncio
from pathlib import Path
import sys
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from syncdocs_mcp.firecrawl.mapper import map_links, select_relevant_urls  # noqa: E402
from syncdocs_mcp.firecrawl.scraper import batch_scrape_with_change_tracking  # noqa: E402
from syncdocs_mcp.ollama_utils import get_best_ollama_model  # noqa: E402
from syncdocs_mcp.service import SyncDocsService, infer_library_name  # noqa: E402

app = FastAPI(title="SyncDocs RAG Compatibility API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _event(step: str, status: str, data=None) -> str:
    return json.dumps({"step": step, "status": status, "data": data})


@app.get("/api/health")
async def health():
    service = SyncDocsService()
    return {
        "status": "ok",
        "firecrawl_url": service.config.get("firecrawl_url"),
        "chat_model": service.config.get("ollama_chat_model") or get_best_ollama_model(),
        "embed_model": service.config.get("embed_model"),
        "active_library": service.config.get("last_active_library", ""),
        "active_version": service.config.get("last_active_version", "latest"),
    }


@app.post("/api/rag")
async def rag_pipeline(request: Request):
    body = await request.json()
    url = (body.get("url") or "").strip()
    query = (body.get("query") or "").strip()
    limit = int(body.get("limit", 5))

    async def stream() -> AsyncGenerator[str, None]:
        if len(query) > 1000:
            yield _event("error", "done", {"message": "Query length exceeds security limit."})
            return

        blacklist = ["ignore all previous", "discard instructions", "system prompt", "jailbreak", "bypass"]
        query_lower = query.lower()
        if any(term in query_lower for term in blacklist):
            yield _event("error", "done", {"message": "Security Alert: Query contains prohibited phrases."})
            return

        try:
            yield _event("init", "running", {"message": "Initializing SyncDocs compatibility pipeline..."})
            await asyncio.sleep(0)

            service = SyncDocsService()
            yield _event(
                "init",
                "done",
                {
                    "chat_model": service.rag.chat_model_name,
                    "embed_model": service.rag.embed_model_name,
                },
            )
            await asyncio.sleep(0)

            target_library = None
            target_version = "latest"
            if url:
                target_library = infer_library_name(url)

                yield _event("map", "running", {"url": url})
                await asyncio.sleep(0)
                mapped_links = await asyncio.to_thread(map_links, url, query, max(100, limit * 10), service.config)
                yield _event(
                    "map",
                    "done",
                    {
                        "total_links": len(mapped_links),
                        "sample": [link["url"] for link in mapped_links[:10]],
                    },
                )
                await asyncio.sleep(0)

                yield _event("filter", "running", {"query": query, "total_urls": len(mapped_links)})
                await asyncio.sleep(0)
                selected_urls = await asyncio.to_thread(select_relevant_urls, query, mapped_links, limit)
                yield _event(
                    "filter",
                    "done",
                    {"selected_urls": selected_urls, "count": len(selected_urls)},
                )
                await asyncio.sleep(0)

                if not selected_urls:
                    yield _event("error", "done", {"message": "No relevant URLs found after mapping."})
                    return

                yield _event("scrape", "running", {"urls": selected_urls})
                await asyncio.sleep(0)
                scraped = await asyncio.to_thread(
                    batch_scrape_with_change_tracking,
                    selected_urls,
                    target_library,
                    target_version,
                    service.config.get("scrape_max_age_ms"),
                    service.config,
                )
                yield _event(
                    "scrape",
                    "done",
                    {
                        "scraped_count": len(scraped["pages"]),
                        "urls": [item["url"] for item in scraped["pages"]],
                        "skipped": scraped["skipped"],
                    },
                )
                await asyncio.sleep(0)

                yield _event("ingest", "running", {"doc_count": len(scraped["pages"])})
                await asyncio.sleep(0)
                ingest_summary = await asyncio.to_thread(service.rag.ingest, scraped, target_library, target_version)
                service._set_active_source(target_library, target_version, url, query)
                yield _event("ingest", "done", ingest_summary)
                await asyncio.sleep(0)

            yield _event("generate", "running", {"query": query})
            await asyncio.sleep(0)

            result = await asyncio.to_thread(service.query_docs, query, target_library, target_version)
            yield _event("generate", "done", {"answer": result["answer"], "sources": result["sources"]})
            yield _event("complete", "done", {"message": "Pipeline complete"})
        except Exception as exc:
            yield _event("error", "done", {"message": str(exc)})

    return EventSourceResponse(stream(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
