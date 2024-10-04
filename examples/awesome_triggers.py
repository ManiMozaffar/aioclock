import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from aioclock import AioClock, At, Depends, Every, Forever, Once
from aioclock.group import Group

# groups.py
group = Group()


def more_useless_than_me():
    return "I'm a dependency. I'm more useless than a screen door on a submarine."


@group.task(trigger=Every(seconds=10))
async def every():
    print("Every 10 seconds, I make a quantum leap. Where will I land next?")


@group.task(trigger=Every(seconds=5))
def even_sync_works():
    print("I'm a synchronous task. I work even in async world.")


@group.task(trigger=At(tz="UTC", hour=0, minute=0, second=0))
async def at():
    print(
        "When the clock strikes midnight... I turn into a pumpkin. Just kidding, I run this task!"
    )


@group.task(trigger=Forever())
async def forever(val: str = Depends(more_useless_than_me)):
    await asyncio.sleep(2)
    print("Heartbeat detected. Still not a zombie. Will check again in a bit.")
    assert val == "I'm a dependency. I'm more useless than a screen door on a submarine."


@group.task(trigger=Once())
async def once():
    print("Just once, I get to say something. Here it goes... I love lamp.")


@asynccontextmanager
async def lifespan(aio_clock: AioClock) -> AsyncGenerator[AioClock]:
    print(
        "Welcome to the Async Chronicles! Did you know a group of unicorns is called a blessing? Well, now you do!"
    )
    yield aio_clock
    print("Going offline. Remember, if your code is running, you better go catch it!")


# app.py
app = AioClock(lifespan=lifespan)
app.include_group(group)


# main.py
if __name__ == "__main__":
    asyncio.run(app.serve())
