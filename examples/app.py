import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
import threading
from time import sleep
from typing import Annotated

from aioclock import AioClock, Depends, Every, Group

# service1.py
group = Group()


def dependency():
    return "Hello from thread: "


@group.task(trigger=Every(seconds=2))
def sync_task_1(val: str = Depends(dependency)):
    print(f"{val} `sync_task_1` {threading.current_thread().ident}")
    sleep(1)  # some blocking operation


@group.task(trigger=Every(seconds=2.01))
def sync_task_2(val: Annotated[str, Depends(dependency)]):
    print(f"{val} `sync_task_2` {threading.current_thread().ident}")
    sleep(1)  # some blocking operation
    return "3"


print(sync_task_2("Aioclock won't color your functions!"))


@group.task(trigger=Every(seconds=2))
async def async_task(val: str = Depends(dependency)):
    print(f"{val} `async_task` {threading.current_thread().ident}")


@asynccontextmanager
async def lifespan(aio_clock: AioClock) -> AsyncGenerator[AioClock]:
    print("Welcome!")
    yield aio_clock
    print("Bye!")


# app.py
app = AioClock(lifespan=lifespan)
app.include_group(group)


if __name__ == "__main__":
    asyncio.run(app.serve())
