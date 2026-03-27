from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from syncdocs_mcp.cli import main  # noqa: E402,F401


if __name__ == "__main__":
    main()
