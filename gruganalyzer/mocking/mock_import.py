from __future__ import annotations

import builtins
from importlib.machinery import PathFinder
import sys
from functools import partial
from types import ModuleType
from unittest.mock import MagicMock


class ModuleWithMocks(ModuleType):
    """
    A module where imported objects can be MagicMock-s
    """

    ...


def build_mock_import(
    project_path_prefix: str,
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

        if globals is None:
            file = None
        else:
            file = globals.get("__file__", None)

        if isinstance(file, str) and not file.startswith(project_path_prefix):
            return bail()

        rootname = name.split(".", 1)[0]
        if (
            rootname in sys.stdlib_module_names  # if stdlib
            or rootname in whitelist_modules  # if explicitly allowed
        ):
            return bail()

        if level > 0:
            res = bail()
            res.__class__ = ModuleWithMocks
            return res

        spec = PathFinder.find_spec(rootname)

        if spec is None:
            bail()  # attempt to raise the normal exception
            raise ModuleNotFoundError(
                f"cant find module '{'.'*level}{name}'. "
                "This is likely not an issue of the analyser but an import system "
                "misunderstanding. Check that you use relative imports or have the "
                "correct sys.path"
            )

        # origin can be none for namespace packages
        if spec.origin is not None:
            spec_path = spec.origin
        else:
            assert spec.submodule_search_locations is not None
            spec_path = spec.submodule_search_locations[0]
        if spec_path.startswith(project_path_prefix):  # if user code
            res = bail()
            res.__class__ = ModuleWithMocks
            return res

        mock = MagicMock(name=name)
        return mock

    return safe_import
