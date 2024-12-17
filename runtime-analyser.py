from __future__ import annotations

from types import ModuleType

from gruganalyser import run


def extract_routes(module: ModuleType):
    return [route.path for route in module.app.routes]


if __name__ == "__main__":
    print(
        run(
            "process",
            "models/test_service/app/main.py",
            ["fastapi", "pydantic"],
            extract_routes,
            timeout=None,
        ),
    )
    print(
        run(
            "plain",
            "models/test_service/app/main.py",
            ["fastapi", "pydantic"],
            extract_routes,
        ),
    )
