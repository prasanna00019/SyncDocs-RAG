from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import click
import requests
from rich.console import Console
from rich.table import Table

from syncdocs_mcp.config import ensure_runtime_dirs, get_config_file, get_stack_dir, load_config, save_config
from syncdocs_mcp.ollama_utils import get_best_ollama_model
from syncdocs_mcp.service import SyncDocsService

console = Console()


def _package_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _copy_docker_assets() -> Path:
    source = _package_root() / "docker"
    target = get_stack_dir()
    target.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, target, dirs_exist_ok=True)
    return target


def _docker_available() -> bool:
    try:
        subprocess.run(["docker", "--version"], check=True, capture_output=True, text=True)
        return True
    except Exception:
        return False


def _start_stack(stack_dir: Path) -> str:
    compose_file = stack_dir / "docker-compose.yml"
    if not compose_file.exists():
        return "docker assets missing"
    try:
        subprocess.run(
            ["docker", "compose", "-f", str(compose_file), "up", "-d"],
            check=True,
            capture_output=True,
            text=True,
        )
        return "started"
    except Exception as exc:
        return f"failed: {exc}"


def _health(url: str) -> str:
    try:
        response = requests.get(url, timeout=3)
        return f"ok ({response.status_code})"
    except requests.RequestException:
        return "unreachable"


@click.group()
def main() -> None:
    """SyncDocs MCP CLI."""


@main.command()
@click.option("--skip-docker", is_flag=True, help="Write config but do not start Docker services.")
@click.option("--chat-model", default="", help="Override the Ollama chat model stored in config.")
def setup(skip_docker: bool, chat_model: str) -> None:
    """Interactive-ish setup for the local stack and config."""
    ensure_runtime_dirs()
    stack_dir = _copy_docker_assets()
    cfg = load_config()
    cfg["ollama_chat_model"] = chat_model or cfg.get("ollama_chat_model") or get_best_ollama_model()
    cfg = save_config(cfg)

    docker_status = "skipped"
    if not skip_docker:
        docker_status = _start_stack(stack_dir) if _docker_available() else "docker not found"

    snippet = {
        "mcpServers": {
            "syncdocs": {
                "command": "python",
                "args": ["-m", "syncdocs_mcp"],
                "cwd": str(_package_root()),
            }
        }
    }

    console.print("[bold green]syncdocs setup complete[/bold green]")
    console.print(f"Config: {get_config_file()}")
    console.print(f"Docker: {docker_status}")
    console.print(f"Ollama chat model: {cfg.get('ollama_chat_model') or '(not found)'}")
    console.print("\nClaude Desktop / Cursor MCP snippet:")
    console.print_json(json.dumps(snippet))


@main.command()
def status() -> None:
    """Show local stack and collection status."""
    service = SyncDocsService()
    data = service.status()

    table = Table(title="SyncDocs Status")
    table.add_column("Item")
    table.add_column("Value")
    table.add_row("Config file", str(get_config_file()))
    table.add_row("Firecrawl", _health((data["config"].get("firecrawl_url") or "").rstrip("/")))
    table.add_row("SearXNG", _health("http://localhost:8080"))
    table.add_row("Active collection", data.get("active_collection") or "(none)")
    console.print(table)

    collection_table = Table(title="Indexed Collections")
    collection_table.add_column("Collection")
    collection_table.add_column("Child Chunks")
    collection_table.add_column("Parent Chunks")
    for item in data["collections"]:
        collection_table.add_row(item["name"], str(item["child_count"]), str(item["parent_count"]))
    if not data["collections"]:
        collection_table.add_row("(none)", "0", "0")
    console.print(collection_table)


@main.command(name="list")
def list_command() -> None:
    """List indexed collections."""
    service = SyncDocsService()
    collections = service.status()["collections"]
    table = Table(title="SyncDocs Collections")
    table.add_column("Collection")
    table.add_column("Child Chunks")
    table.add_column("Parent Chunks")
    for item in collections:
        table.add_row(item["name"], str(item["child_count"]), str(item["parent_count"]))
    if not collections:
        table.add_row("(none)", "0", "0")
    console.print(table)


@main.command()
@click.argument("library")
@click.argument("version", default="latest")
def clear(library: str, version: str) -> None:
    """Delete a specific indexed collection."""
    service = SyncDocsService()
    service.clear_collection(library, version)
    console.print(f"Cleared collection for {library}:{version}")


@main.command()
@click.argument("library")
@click.argument("version", default="latest")
@click.option("--url", default="", help="Override the stored source URL.")
@click.option("--query", default="", help="Override the stored source query.")
def refresh(library: str, version: str, url: str, query: str) -> None:
    """Re-index a collection using stored source metadata and change tracking."""
    service = SyncDocsService()
    result = service.refresh(library, version=version, url=url or None, query=query or None)
    console.print_json(json.dumps(result))
