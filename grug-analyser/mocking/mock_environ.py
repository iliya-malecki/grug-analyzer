from __future__ import annotations
import os
import inspect


def build_mock_getitem(project_root_module: str):
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
        if not frame.f_back.f_globals["__package__"].startswith(project_root_module):
            return original_getitem(self, key)

        try:
            return original_getitem(self, key)
        except KeyError:
            return self.decodevalue(b"__mocked__")

    return mock_getitem
