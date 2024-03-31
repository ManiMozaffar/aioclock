import asyncio

from aioclock import AioClock, Depends, Every, Group

# service1.py
group = Group()


def dependency():
    return "Hello, world!"


def overwritten_dependency():
    return "Goodbye, world!"


@group.task(trigger=Every(seconds=1))
async def my_task(val: str = Depends(dependency)):
    print(val)


# app.py
app = AioClock()
app.include_group(group)


app.override_dependencies(dependency, overwritten_dependency)

if __name__ == "__main__":
    asyncio.run(app.serve())
