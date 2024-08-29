import asyncio
from contextlib import contextmanager
from datetime import datetime

import pytest

from aioclock import AioClock, Once

app = AioClock()


@contextmanager
def assert_execution_time_below(target: float):
    start_time = datetime.now()
    yield
    assert (datetime.now() - start_time).total_seconds() < target


@app.task(trigger=Once(), timeout=0.1)
async def main():
    await asyncio.sleep(10)


@pytest.mark.asyncio
async def test_run_manual():
    task_with_timeout = app._get_tasks()[0]
    with assert_execution_time_below(0.5):
        await task_with_timeout.run()
