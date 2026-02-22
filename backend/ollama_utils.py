import requests

# Cloud models can only do chat, NOT embeddings
CLOUD_MODELS = {"minimax-m2.5:cloud", "kimi-k2.5:cloud", "glm-5:cloud"}

# Preferred models for chat (cloud models are fine here)
PREFERRED_CHAT_MODELS = ["minimax-m2.5:cloud", "kimi-k2.5:cloud", "glm-5:cloud", "gemma3:4b"]

# Preferred models for embeddings (must be LOCAL models with actual weights)
PREFERRED_EMBEDDING_MODELS = ["mxbai-embed-large", "nomic-embed-text", "all-minilm"]


def _get_available_models():
    """Fetch all available models from local Ollama."""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        if response.status_code == 200:
            models = response.json().get("models", [])
            return [model["name"] for model in models]
        else:
            print(f"Error connecting to local Ollama instance. Status: {response.status_code}")
            return []
    except requests.exceptions.RequestException:
        print("Error connecting to local Ollama instance. Please ensure it is running at http://localhost:11434")
        return []


def get_best_ollama_model() -> str:
    """
    Selects the best model for CHAT / LLM tasks.
    Cloud-routed models are fine here.
    """
    available = _get_available_models()
    if not available:
        return ""

    for pref in PREFERRED_CHAT_MODELS:
        if pref in available:
            print(f"[Ollama] Selected chat model: {pref}")
            return pref

    fallback = available[0]
    print(f"[Ollama] Preferred chat models not found. Falling back to: {fallback}")
    return fallback


def get_embedding_model() -> str:
    """
    Selects the best model for EMBEDDINGS.
    Cloud-routed models CANNOT generate embeddings, so they are excluded.
    """
    available = _get_available_models()
    if not available:
        return ""

    # Filter out cloud models — they don't support /api/embed
    local_models = [m for m in available if m not in CLOUD_MODELS]

    if not local_models:
        print("Warning: No local models found for embeddings. Cloud models cannot generate embeddings.")
        print("Please pull a local model: ollama pull nomic-embed-text  OR  ollama pull gemma3:4b")
        return ""

    for pref in PREFERRED_EMBEDDING_MODELS:
        if pref in local_models:
            print(f"[Ollama] Selected embedding model: {pref}")
            return pref

    fallback = local_models[0]
    print(f"[Ollama] Preferred embedding models not found. Falling back to: {fallback}")
    return fallback
