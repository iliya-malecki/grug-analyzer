# Grug analyzer
Have you ever had genius colleagues that have very huge brains and can thus remember all kinds of special behaviors about their systems? Have you ever spent a night trying to test such a clever codebase since it has a huge ML model in global scope, or some environment variable birdsnest, which stops you from even importing it, let alone testing? All with your normal-sized grug brain? Hopefully, you managed to find and mock all the environment variables, but oh no now the entire runtime dies because it loads this big object in memory in this special case and smirkly OOMs :)

Well youll have none of that now (or at least, less of that)!

## What it does

Grug analyzer has incredible grug power: it uses a whitelist approach to load only a defined and expected subset of modules into memory and __everything__ else will be mocked by monkeypatching the import system. There will be no unexpected heavyweight objects since all of them will turn into MagicMocks, there will be no env variable lookups since they will all have the default value of `__mocked__`.

## How to use

To analyse the lazy-loaded module and extract the necessary information, you will define a simple callback that extracts whatever you want out of the module and returns it to you for further processing. Grug analyzer then runs module building and your extractor callback in a subprocess, so even if you OOM, you can recover, reduce the whitelist, and gracefully try extracting again. The return value will be dill-pickled before getting sent back to you, so you can return almost anything you want.

"What? but my clever module doesnt OOM! Just give me the lazy module and dont tell me what to do" you might say. Worry not, you can return the entire module out of your extractor callback and swap out the `process` runner for the `plain` one and avoid the entire serialization dance.

## Examples

Take a look at the example of using grug analyzer to pull out routes out of a fastapi app
```python
from gruganalyser import run, MockedModule


def extract_routes(module: MockedModule):
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

```

