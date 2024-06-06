# AioClock

## The Principle

Scheduling is annoying, stateful and hard to scale. But not anymore! AioClock is here as an asyncio-based scheduling framework designed for execution of periodic task with integrated support for dependency injection, enabling efficient and flexiable task management.

Aioclock offers:

- Async: 100% Async, very light, fast and resource friendly
- Scheduling: Keep scheduling tasks for you
- Group: Group your task, for better code maintainability
- Trigger: Already defined and easily extendable triggers, to trigger your scheduler to be started
- Easy syntax: Library's syntax is very easy and enjoyable, no confusing hierarchy
- Pydantic v2 validation: Validate all your trigger on startup using pydantic 2. Fastest to fail possible!
- **Soon**: Running the task dispatcher (scheduler) on different process by default, so CPU intensive stuff on task won't delay the scheduling
- **Soon**: Backend support, to allow horizontal scalling, by synchronizing, maybe using Redis

## Getting started

To Install aioclock, simply do

```
pip install aioclock
```

AioClock is very user friendly and easy to use, it's type stated library to use easily.
AioClock always have a trigger, that trigger the events.

```python
import asyncio

from aioclock import AioClock, At, Depends, Every, Forever, Once, OnShutDown, OnStartUp
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


# app.py
app = AioClock()
app.include_group(group)


@app.task(trigger=OnStartUp())
async def startup():
    print(
        "Welcome to the Async Chronicles! Did you know a group of unicorns is called a blessing? Well, now you do!"
    )


@app.task(trigger=OnShutDown())
async def shutdown():
    print("Going offline. Remember, if your code is running, you better go catch it!")


# main.py
if __name__ == "__main__":
    asyncio.run(app.serve())
```
