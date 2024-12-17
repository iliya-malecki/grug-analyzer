from __future__ import annotations

import builtins
import importlib
import importlib.util
import sys
from functools import partial
from types import ModuleType
from unittest.mock import MagicMock


class MockedModule(ModuleType):
    def __repr__(self) -> builtins.str:
        return f"mocked<{super().__repr__()}>"


def build_mock_import(
    project_root_dir_absolute: str,
    whitelist_modules: set[str],
):
    original_import = builtins.__import__

    def safe_import(
        name: str,
        globals: dict | None = None,
        locals: dict | None = None,
        fromlist=(),
        level=0,
    ):
        # bail() is calling the original implementation of __import__, nothing curious
        bail = partial(
            original_import,
            name=name,
            globals=globals,
            locals=locals,
            fromlist=fromlist,
            level=level,
        )

        # we use package to see if we are in user provided code
        if globals is None:
            package = None
            file = None
        else:
            package = globals.get("__package__", None)
            file = globals.get("__file__", None)


        if isinstance(file, str) and not file.startswith(project_root_dir_absolute):
            return bail()

        # we get here only if we are importing from user code
        spec = importlib.util.find_spec(f"{'.'*level}{name}", package=package)
        if spec is None:
            raise ModuleNotFoundError(
                f"cant find module '{'.'*level}{name}' for package = '{package}'. "
                f"This is likely not an issue of the analyser but an absolute import. "
                f"Use relative imports because from this tool's perspective all code "
                f"is in submodules of the package in '{project_root_dir_absolute}'"
            )

        if (
            spec.name in sys.stdlib_module_names  # if stdlib
            or spec.origin is None  # if stdlib
            or spec.name.split(".")[0] in whitelist_modules  # if explicitly allowed
        ):
            return bail()

        if spec.origin.startswith(project_root_dir_absolute):  # if user code
            res = bail()
            res.__class__ = MockedModule
            return res

        # at this point this is an absolute import
        # TODO: simplify the code addressing that
        mock = MagicMock(name=name)
        mock.__spec__ = spec
        return mock

    return safe_import
