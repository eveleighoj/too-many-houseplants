"""Writes each sub-app's OpenAPI spec to <dir>/<sub-app>.json, without running a server.

    uv run python -m houseplants.export_openapi <dir>

Used to check the frontends' generated API types are up to date (`make api-types-check`).
"""

import json
import sys
from pathlib import Path

from houseplants.main import SUB_APPS


def export(directory: Path) -> list[Path]:
    directory.mkdir(parents=True, exist_ok=True)
    written = []
    for prefix, app in SUB_APPS.items():
        path = directory / f"{prefix}.json"
        path.write_text(json.dumps(app.openapi(), indent=2) + "\n")
        written.append(path)
    return written


if __name__ == "__main__":
    for path in export(Path(sys.argv[1])):
        print(f"Wrote {path}")
