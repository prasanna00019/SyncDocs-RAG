from __future__ import annotations

import requests

CLOUD_MODELS = {"minimax-m2.5:cloud", "kimi-k2.5:cloud", "glm-5:cloud"}
PREFERRED_CHAT_MODELS = ["minimax-m2.5:cloud", "kimi-k2.5:cloud", "glm-5:cloud", "gemma3:4b"]
PREFERRED_EMBEDDING_MODELS = [
    "embeddinggemma:300m",
    "mxbai-embed-large:latest",
    "nomic-embed-text",
    "all-minilm",
]


def _get_available_models() -> list[str]:
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        response.raise_for_status()
    except requests.RequestException:
        return []
    payload = response.json()
    return [model.get("name", "") for model in payload.get("models", []) if model.get("name")]


def get_best_ollama_model() -> str:
    available = _get_available_models()
    if not available:
        return ""
    for preferred in PREFERRED_CHAT_MODELS:
        if preferred in available:
            return preferred
    return available[0]


def get_embedding_model() -> str:
    available = _get_available_models()
    if not available:
        return ""
    local_models = [model for model in available if model not in CLOUD_MODELS]
    if not local_models:
        return ""
    for preferred in PREFERRED_EMBEDDING_MODELS:
        if preferred in local_models:
            return preferred
    return local_models[0]
