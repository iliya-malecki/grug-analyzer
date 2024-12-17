from __future__ import annotations
from pathlib import Path


def find_package_boundary(path: Path):
    while True:  # path will raise if it goes south
        if not (path.parent / "__init__.py").exists():
            return path
        path = path.parent
