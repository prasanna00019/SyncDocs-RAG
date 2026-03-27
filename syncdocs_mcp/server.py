from __future__ import annotations

from typing import Any

from syncdocs_mcp.service import SyncDocsService


def create_mcp_server(service: SyncDocsService | None = None):
    from mcp.server.fastmcp import FastMCP

    syncdocs = FastMCP("syncdocs-mcp")
    svc = service or SyncDocsService()

    @syncdocs.tool()
    def search_web(query: str, limit: int = 5) -> list[dict[str, str]]:
        return svc.search_web(query=query, limit=limit)

    @syncdocs.tool()
    def fetch_and_index(
        url: str,
        library: str,
        query: str,
        version: str = "latest",
    ) -> dict[str, Any]:
        return svc.fetch_and_index(url=url, query=query, library=library, version=version)

    @syncdocs.tool()
    def query_docs(query: str, library: str, version: str = "latest") -> dict[str, Any]:
        return svc.query_docs(query=query, library=library, version=version)

    return syncdocs


def main() -> None:
    server = create_mcp_server()
    server.run()
