import asyncio

from aioclock import AioClock, Depends, Every, Group, OnShutDown, OnStartUp

# service1.py
group = Group()


def dependency():
    return "Hello, world!"


@group.task(trigger=Every(seconds=1))
async def my_task(val: str = Depends(dependency)):
    print(val)


# app.py
app = AioClock()
app.include_group(group)


@app.task(trigger=OnStartUp())
async def startup(val: str = Depends(dependency)):
    print("Welcome!")


@app.task(trigger=OnShutDown())
async def shutdown(val: str = Depends(dependency)):
    print("Bye!")


if __name__ == "__main__":
    asyncio.run(app.serve())
