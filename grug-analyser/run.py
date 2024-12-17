from __future__ import annotations
import importlib
import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Callable, TypeVar
from unittest.mock import patch

from .mocking import MockedModule, build_mock_getitem, build_mock_import
from .runners import RunnerKind, registry
from .util import find_package_boundary

T = TypeVar("T")


def analyse_module(
    module_path: str,
    whitelist_modules: list[str],
    extractor: Callable[[ModuleType], T],
) -> T:
    project_root_dir = str(find_package_boundary(Path(module_path)))
    project_root_module = project_root_dir.replace("/", ".")
    project_root_dir_absolute = str(Path(project_root_dir).absolute())
    with patch(
        "builtins.__import__",
        build_mock_import(
            project_root_module=project_root_module,
            project_root_dir_absolute=project_root_dir_absolute,
            whitelist_modules=set(whitelist_modules),
        ),
    ), patch(
        "os._Environ.__getitem__",
        build_mock_getitem(
            project_root_module=project_root_module,
        ),
    ):
        module = importlib.import_module(module_path)
        # due to instrumenting below importlib, the root is skipped
        module.__class__ = MockedModule
        return extractor(module)


def run(
    runner_kind: RunnerKind,
    module_path: str,
    whitelist_modules: list[str],
    extractor: Callable[[ModuleType], T],
    *runner_args,
    **runner_kwargs,
) -> T:
    return registry[runner_kind](*runner_args, **runner_kwargs).run(
        analyse_module,
        module_path=module_path,
        whitelist_modules=whitelist_modules,
        extractor=extractor,
    )
