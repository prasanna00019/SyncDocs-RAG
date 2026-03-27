from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from syncdocs_mcp.ollama_utils import get_best_ollama_model, get_embedding_model  # noqa: E402,F401
