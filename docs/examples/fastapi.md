To run AioClock with FastAPI, you can run it in the background with FastAPI lifespan, next to your asgi.

```python
from aioclock import AioClock
from fastapi import FastAPI
import asyncio

clock_app = AioClock()

async def lifespan(app: FastAPI):
    task = asyncio.create_task(clock_app.serve())
    yield

    try:
        task.cancel()
        await task
    except asyncio.CancelledError:
        ...

app = FastAPI(lifespan=lifespan)
```

!!! danger "This setup is not recommended at all"

    Running AioClock with FastAPI is not a good practice in General, because:
    FastAPI is a framework to write stateless API, but aioclock is still stateful component in your architecture.
    In simpler terms, it means if you have 5 instances of aioclock running, they produce 5x tasks than you intended.
    So you cannot easily scale up horizontally by adding more aioclock power!

    Even in this case, if you serve FastAPI with multiple processes, you end up having one aioclock per process!

    What I suggest doing is to spin one new service, that is responsible for processing the periodic tasks.
    Try to avoid periodic tasks in general, but sometimes it's not easy to do so.
