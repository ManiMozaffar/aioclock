import pytest

from aioclock import AioClock, Depends, Once, run_with_injected_deps

app = AioClock()


def some_dependency():
    return 1


@app.task(trigger=Once())
async def main(bar: int = Depends(some_dependency)):
    print("Hello World")
    return bar


@pytest.mark.asyncio
async def test_run_manual():
    foo = await run_with_injected_deps(main)
    assert foo == 1
