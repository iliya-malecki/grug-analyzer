from gruganalyzer import run, ModuleWithMocks, ProcessRunner


def extract_routes(module: ModuleWithMocks):
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
