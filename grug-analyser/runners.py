from __future__ import annotations

import itertools
import queue
from abc import ABC, abstractmethod
from functools import wraps
from typing import TYPE_CHECKING, Callable, Literal, ParamSpec, TypeVar

if TYPE_CHECKING:
    from multiprocessing import Process, Queue
else:
    from multiprocess import Process, Queue


P = ParamSpec("P")
T = TypeVar("T")

RunnerKind = Literal["process", "plain"]

registry: dict[RunnerKind, type[Runner]] = {}


class Runner(ABC):
    @abstractmethod
    def run(
        self,
        target_function: Callable[P, T],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> T: ...

    def __init_subclass__(cls, key: RunnerKind) -> None:
        assert cls.__name__.lower().startswith(key)
        registry[key] = cls


class ProcessRunner(Runner, key="process"):
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


class PlainRunner(Runner, key="plain"):
    def run(
        self,
        target_function: Callable[P, T],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> T:
        return target_function(*args, **kwargs)
