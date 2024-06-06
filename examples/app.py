import asyncio
import threading
from time import sleep
from typing import Annotated

from aioclock import AioClock, Depends, Every, Group, OnShutDown, OnStartUp

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


print(sync_task_2("Aioclock won't color your functions! "))


@group.task(trigger=Every(seconds=2))
async def async_task(val: str = Depends(dependency)):
    print(f"{val} `async_task` {threading.current_thread().ident}")


# app.py
app = AioClock()
app.include_group(group)


@app.task(trigger=OnStartUp())
def startup(val: str = Depends(dependency)):
    print("Welcome!")


@app.task(trigger=OnShutDown())
def shutdown(val: str = Depends(dependency)):
    print("Bye!")


if __name__ == "__main__":
    asyncio.run(app.serve())
