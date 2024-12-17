from __future__ import annotations

import importlib
import importlib.util
import sys
from pathlib import Path
from typing import Callable, TypeVar, cast
from unittest.mock import patch

from .mocking import MockedModule, build_mock_getitem, build_mock_import
from .runners.runners import Runner
from .util import find_package_boundary

T = TypeVar("T")


def analyse_module(
    module_path: str,
    whitelist_modules: list[str],
    extractor: Callable[[MockedModule], T],
    project_root_dir: str | None = None,
) -> T:
    resolved_module = Path(module_path).resolve()
    if not Path(resolved_module).exists():
        raise FileNotFoundError(f"File {resolved_module} does not exist")
    if project_root_dir is None:
        project_root_dir = str(find_package_boundary(resolved_module))
    module_dotted_path = (
        str(resolved_module)
        .removeprefix(project_root_dir)
        .removeprefix("/")
        .removesuffix(".py")
        .replace("/", ".")
    )

    with patch(
        "builtins.__import__",
        build_mock_import(
            project_root_dir_absolute=project_root_dir,
            whitelist_modules=set(whitelist_modules),
        ),
    ), patch(
        "os._Environ.__getitem__",
        build_mock_getitem(
            project_root_dir_absolute=project_root_dir,
        ),
    ):
        original_sys_path = sys.path.copy()
        try:
            sys.path.append(project_root_dir)
            module = importlib.import_module(module_dotted_path)
        finally:
            sys.path = original_sys_path
        # due to instrumenting below importlib, the root is skipped
        module.__class__ = MockedModule
        return extractor(cast(MockedModule, module))


def run(
    runner: Runner,
    module_path: str,
    whitelist_modules: list[str],
    extractor: Callable[[MockedModule], T],
    project_root_dir: str | None = None,
) -> T:
    return runner.run(
        analyse_module,
        module_path=module_path,
        whitelist_modules=whitelist_modules,
        extractor=extractor,
        project_root_dir=project_root_dir,
    )
