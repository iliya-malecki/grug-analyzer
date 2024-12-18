from gruganalyzer import run, ModuleWithMocks


def extract_routes(module: ModuleWithMocks):
    return [route.path for route in module.app.routes]


if __name__ == "__main__":
    print(
        run(
            module_path="test-service/app/main.py",
            whitelist_modules=["fastapi", "pydantic"],
            extractor=extract_routes,
            mocked_env_value=b"42",
        ),
    )
