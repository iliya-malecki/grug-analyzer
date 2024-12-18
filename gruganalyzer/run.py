from __future__ import annotations

import importlib
import importlib.util
import sys
from pathlib import Path
from typing import Callable, TypeVar, cast
from unittest.mock import patch

from .mocking import ModuleWithMocks, build_mock_getitem, build_mock_import
from .runners.runners import Runner
from .runners import ProcessRunner
from .util import find_package_boundary

T = TypeVar("T")


def analyse_module(
    module_path: str,
    whitelist_modules: list[str],
    extractor: Callable[[ModuleWithMocks], T],
    project_boundary: str | None = None,
    allow_uninstalled=False,
) -> T:
    resolved_module = Path(module_path).resolve()
    if not resolved_module.exists():
        raise FileNotFoundError(f"File {resolved_module} does not exist")
    if project_boundary is None:
        project_boundary = str(find_package_boundary(resolved_module))
    module_dotted_path = (
        str(resolved_module)
        .removeprefix(project_boundary)
        .removeprefix("/")
        .removesuffix(".py")
        .replace("/", ".")
    )
    package_root = module_dotted_path.split(".", 1)[0]

    with patch(
        "builtins.__import__",
        build_mock_import(
            project_path_prefix=f"{project_boundary}/{package_root}",
            whitelist_modules=set(whitelist_modules),
            allow_uninstalled=allow_uninstalled,
        ),
    ), patch(
        "os._Environ.__getitem__",
        build_mock_getitem(
            project_path_prefix=f"{project_boundary}/{package_root}",
        ),
    ):
        original_sys_path = sys.path.copy()
        try:
            sys.path.append(project_boundary)
            module = importlib.import_module(module_dotted_path)
        finally:
            sys.path = original_sys_path
        # due to instrumenting below importlib, the root is skipped
        module.__class__ = ModuleWithMocks
        return extractor(cast(ModuleWithMocks, module))


def run(
    *,
    runner: Runner = ProcessRunner(timeout=None),
    module_path: str,
    whitelist_modules: list[str],
    extractor: Callable[[ModuleWithMocks], T],
    project_boundary: str | None = None,
    allow_uninstalled=False,
) -> T:
    return runner.run(
        analyse_module,
        module_path=module_path,
        whitelist_modules=whitelist_modules,
        extractor=extractor,
        project_boundary=project_boundary,
        allow_uninstalled=allow_uninstalled,
    )
