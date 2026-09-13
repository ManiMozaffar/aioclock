from contextlib import asynccontextmanager, contextmanager

import pytest

from aioclock import AioClock, Depends
from aioclock.triggers import Once

ML_MODEL_ASYNC = []
RAN_ONCE_TASK_ASYNC = False


@asynccontextmanager
async def lifespan(app: AioClock):
    ML_MODEL_ASYNC.append(2)
    yield app
    ML_MODEL_ASYNC.clear()


app = AioClock(lifespan=lifespan)


@app.task(trigger=Once())
async def main():
    assert len(ML_MODEL_ASYNC) == 1
    global RAN_ONCE_TASK_ASYNC
    RAN_ONCE_TASK_ASYNC = True


@pytest.mark.asyncio
async def test_lifespan_e2e_async():
    assert len(ML_MODEL_ASYNC) == 0
    assert RAN_ONCE_TASK_ASYNC is False
    await app.serve()  # asserts are in the task
    assert len(ML_MODEL_ASYNC) == 0  # clean up done
    assert RAN_ONCE_TASK_ASYNC is True  # task ran


ML_MODEL_SYNC = []  # just some imaginary component that needs to be started and stopped
RAN_ONCE_TASK_SYNC = False


@contextmanager
def lifespan_sync(sync_app: AioClock):
    ML_MODEL_SYNC.append(2)
    yield sync_app
    ML_MODEL_SYNC.clear()


sync_app = AioClock(lifespan=lifespan_sync)


@sync_app.task(trigger=Once())
def sync_main():
    assert len(ML_MODEL_SYNC) == 1
    global RAN_ONCE_TASK_SYNC
    RAN_ONCE_TASK_SYNC = True


@pytest.mark.asyncio
async def test_lifespan_e2e_sync():
    assert len(ML_MODEL_SYNC) == 0
    assert RAN_ONCE_TASK_SYNC is False
    await sync_app.serve()  # asserts are in the task
    assert len(ML_MODEL_SYNC) == 0  # clean up done
    assert RAN_ONCE_TASK_SYNC is True  # task ran


@pytest.mark.asyncio
async def test_async_lifespan_dependencies_are_injected():
    injected_values = []

    def dependency():
        return "injected"

    @asynccontextmanager
    async def lifespan_with_dependency(app: AioClock, value: str = Depends(dependency)):
        injected_values.append(value)
        yield app

    app_with_dependency = AioClock(lifespan=lifespan_with_dependency)

    await app_with_dependency.serve()

    assert injected_values == ["injected"]


@pytest.mark.asyncio
async def test_sync_lifespan_dependencies_are_injected():
    injected_values = []

    def dependency():
        return "injected"

    @contextmanager
    def lifespan_with_dependency(app: AioClock, value: str = Depends(dependency)):
        injected_values.append(value)
        yield app

    app_with_dependency = AioClock(lifespan=lifespan_with_dependency)

    await app_with_dependency.serve()

    assert injected_values == ["injected"]


@pytest.mark.asyncio
async def test_lifespan_dependency_overrides_are_applied():
    injected_values = []

    def dependency():
        return "original"

    def override():
        return "overridden"

    @asynccontextmanager
    async def lifespan_with_dependency(app: AioClock, value: str = Depends(dependency)):
        injected_values.append(value)
        yield app

    app_with_dependency = AioClock(lifespan=lifespan_with_dependency)
    app_with_dependency.override_dependencies(dependency, override)

    await app_with_dependency.serve()

    assert injected_values == ["overridden"]
