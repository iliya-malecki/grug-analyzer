from __future__ import annotations

import inspect
import os


def build_mock_getitem(project_path_prefix: str, mocked_value: bytes):
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
        if not frame.f_back.f_globals["__file__"].startswith(project_path_prefix):
            return original_getitem(self, key)

        try:
            return original_getitem(self, key)
        except KeyError:
            return self.decodevalue(mocked_value)

    return mock_getitem
