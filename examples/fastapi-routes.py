from gruganalyser import run, MockedModule, ProcessRunner


def extract_routes(module: MockedModule):
    return [route.path for route in module.app.routes]


if __name__ == "__main__":
    print(
        run(
            ProcessRunner(timeout=None),
            "models/test_service/app/main.py",
            ["fastapi", "pydantic"],
            extract_routes,
        ),
    )
