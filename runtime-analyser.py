from __future__ import annotations
import builtins
import importlib
import importlib.util
import inspect
import os
import sys
from functools import partial, wraps
from pathlib import Path
from typing import Callable, Any, TYPE_CHECKING, ParamSpec, TypeVar
from types import ModuleType
from unittest.mock import MagicMock, patch
import itertools
import queue
from abc import ABC, abstractmethod

if TYPE_CHECKING:
    from multiprocessing import Queue, Process
else:
    from multiprocess import Queue, Process


P = ParamSpec("P")
T = TypeVar("T")


WHITELIST_MODULES = {"fastapi", "pydantic"}


class MockedModule(ModuleType):
    def __repr__(self) -> builtins.str:
        return f"mocked<{super().__repr__()}>"


def build_safe_import(
    project_module: str,
    project_dir_full_path: str,
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
        else:
            package = globals.get("__package__", None)

        if isinstance(package, str) and not package.startswith(project_module):
            return bail()

        # we get here only if we are importing from user code
        spec = importlib.util.find_spec(f"{'.'*level}{name}", package=package)
        if spec is None:
            raise ModuleNotFoundError(
                f"cant find module '{'.'*level}{name}' for package = '{package}'. "
                f"This is likely not an issue of the analyser but an absolute import. "
                f"Use relative imports because from this tool's perspective all code "
                f"is in submodules of the '{project_module}' module"
            )

        if (
            spec.name in sys.stdlib_module_names  # if stdlib
            or spec.origin is None  # if stdlib
            or spec.name.split(".")[0] in whitelist_modules  # if explicitly allowed
        ):
            return bail()

        if spec.origin.startswith(project_dir_full_path):  # if user code
            res = bail()
            res.__class__ = MockedModule
            return res

        return MagicMock(name=name)

    return safe_import


def build_mock_getitem(project_module: str):
    original_getitem = os._Environ.__getitem__

    def mock_getitem(self: os._Environ, key):
        frame = inspect.currentframe()
        if frame is None or frame.f_back is None:
            raise ValueError(
                # there is no way this function has no caller
                f"no stack frame information available or it is corrupted: "
                f"{frame = }, {frame and frame.f_back = }"
            )

        # dont touch other peoples code
        if not frame.f_back.f_globals["__package__"].startswith(project_module):
            return original_getitem(self, key)

        try:
            return original_getitem(self, key)
        except KeyError:
            return self.decodevalue(b"__mocked__")

    return mock_getitem


def analyse_module(
    project_dir_path: str,
    entrypoint_module: str,
    additional_whitelist_modules: list[str],
    extractor: Callable[[ModuleType], Any],
):
    project_module = project_dir_path.replace("/", ".")
    project_dir_full_path = str(Path(project_dir_path).absolute())
    with patch(
        "builtins.__import__",
        build_safe_import(
            project_module=project_module,
            project_dir_full_path=project_dir_full_path,
            whitelist_modules=WHITELIST_MODULES.union(additional_whitelist_modules),
        ),
    ), patch(
        "os._Environ.__getitem__",
        build_mock_getitem(
            project_module=project_module,
        ),
    ):
        module = importlib.import_module(
            f"{project_dir_path.replace('/','.')}.{entrypoint_module}"
        )
        # due to instrumenting below importlib, the root is skipped
        module.__class__ = MockedModule
        return extractor(module)


class Runner(ABC):
    @abstractmethod
    def run(
        self,
        target_function: Callable[P, T],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> T: ...


class ProcessRunner(Runner):
    def __init__(
        self,
        timeout: float | None,
    ) -> None:
        self.timeout = timeout

    def run(
        self,
        target_function: Callable[P, T],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> T:
        @wraps(target_function)
        def wrapper(q: Queue, *args: P.args, **kwargs: P.kwargs):
            try:
                q.put((target_function(*args, **kwargs), None))
            except Exception as e:
                q.put((None, e))

        q = Queue()
        process = Process(target=wrapper, args=(q, *args), kwargs=kwargs)
        process.start()

        frequency = 0.2
        if self.timeout is None:
            counter = itertools.count()
        else:
            counter = range(max(1, int(self.timeout / frequency)))
        for _ in counter:
            try:
                ok, err = q.get(timeout=frequency)
            except queue.Empty:
                if not process.is_alive():
                    raise ChildProcessError(
                        "The subprocess loading your code crashed, likely due to an OOM. "
                        "Hint: if you have heavy objects in global scope of your (sub)modules, "
                        "dont whitelist them for full import and let them lazyload"
                    )
                else:
                    continue
            if err is not None:
                raise err

            return ok
        raise TimeoutError(
            f"{target_function.__name__} Timed out after {self.timeout} seconds"
        )


class PlainRunner:
    def run(
        self,
        target_function: Callable[P, T],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> T:
        return target_function(*args, **kwargs)


def extract_routes(module: ModuleType):
    return [route.path for route in module.app.routes]


if __name__ == "__main__":
    print(
        ProcessRunner(1).run(
            analyse_module, "models/test_service", "app.main", [], extract_routes
        ),
    )

    print(
        PlainRunner().run(
            analyse_module, "models/test_service", "app.main", [], extract_routes
        ),
    )
