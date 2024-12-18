from __future__ import annotations

from pathlib import Path


def find_package_boundary(absolute_path: Path):
    assert absolute_path.is_absolute()
    while True:  # path will raise if it goes south
        if not (absolute_path.parent / "__init__.py").exists():
            return absolute_path.parent
        absolute_path = absolute_path.parent
