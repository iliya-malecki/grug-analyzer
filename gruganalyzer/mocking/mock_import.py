from __future__ import annotations

import builtins
from importlib.machinery import PathFinder
import sys
from functools import partial
from types import ModuleType
from unittest.mock import MagicMock
from pathlib import Path


class ModuleWithMocks(ModuleType):
    """
    A module where imported objects can be MagicMock-s
    """

    ...


# decided against subclassing since all interesting objects
# will be a.long.chain.away.from.module, and __class__ shenanigans dont go well
# with MagicMock.__getattr__
# (Thus i cant return MagicMock from my subclass __getattr__ without fully reimplementing it)
def MockedModule(name: str, spec):
    mock = MagicMock(name=name)
    mock.__spec__ = spec
    return mock


def is_mocked_module(mock: MagicMock):
    return hasattr(mock, "__spec__")


def build_mock_import(
    project_path_prefix: str,
    whitelist_modules: set[str],
    allow_uninstalled=False,
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
            if not allow_uninstalled:
                bail()  # attempt to raise the normal exception
                raise ModuleNotFoundError(
                    f"cant find module '{'.'*level}{name}'. "
                    "This is likely not an issue of the analyser but an import system "
                    "misunderstanding. Check that you use relative imports or have the "
                    "correct sys.path"
                )
            else:
                if file is None:
                    raise ModuleNotFoundError(
                        f"cant find neither '{rootname}' module nor __file__ in caller "
                        "globals, this makes no sense"
                    )
                for sibling in Path(file).parent.iterdir():
                    if sibling.name.removesuffix(".py") == rootname:
                        raise ModuleNotFoundError(
                            f"there is '{rootname}' module in {Path(file).parent} "
                            "but python's import system failed to find it. "
                            "Either make your imports relative, or fix your sys.path, "
                            "or install your missing package "
                            "(if you meant it as a site package) - "
                            "current setup is ambiguous"
                        )

                return MockedModule(name, spec)

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

        return MockedModule(name, spec)

    return safe_import
