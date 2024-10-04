You can basically run any tasks on aioclock, it could be your redis broker or other kind of brokers listening to a queue. The benefit of doing so, is that you don't need to worry about dependency injection, shutdown or startup event.

AioClock offer you a unique easy way to spin up new services, without any overhead or perfomance issue!

```python
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from aioclock import AioClock, Forever, Depends
from functools import lru_cache
from typing import NewType

BrokerType = NewType("BrokerType", ...) # your broker type ...

# your singleton redis instance
@lru_cache
def get_redis():
    ...

@asynccontextmanager
async def lifespan(aio_clock: AioClock, redis: BrokerType = Depends(get_redis)) -> AsyncGenerator[AioClock]:
    yield aio_clock
    await redis.disconnect()


app = AioClock(lifespan=lifespan)


@app.task(trigger=Forever())
async def read_message_queue(redis: BrokerType = Depends(get_redis)):
    async for message in redis.listen("..."):
        ...

```

One other way to do this, is to implement a trigger that automatically execute the function.
But to do so, I basically need to wrap redis in my own library, and that's not good for some reasons:

1. Complexity of framework increases.
2. Is not realy flexible, because native library and client are always way more flexible. I end up writing something like `Celery`.
3. The architecture I choose to handle interactions with broker may not satisfy your requirement.

[This repository is an example how you can write a message queue in aioclock.](https://github.com/ManiMozaffar/typed-redis)
