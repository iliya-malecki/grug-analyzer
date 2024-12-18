from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable, ParamSpec, TypeVar

P = ParamSpec("P")
T = TypeVar("T")


class Runner(ABC):
    @abstractmethod
    def run(
        self,
        target_function: Callable[P, T],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> T: ...
