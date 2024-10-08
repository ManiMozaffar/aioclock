import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from aioclock import AioClock
from aioclock.ext.fast import make_fastapi_router
from aioclock.triggers import Every


@asynccontextmanager
async def aioclock_lifespan(aio_clock: AioClock) -> AsyncGenerator[AioClock]:
    print("Starting aiolcok app...")
    yield aio_clock
    print("Closing aiolcok app...")


clock_app = AioClock(lifespan=aioclock_lifespan)


@clock_app.task(trigger=Every(seconds=3600))
async def foo():
    print("Foo is processing...")


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(clock_app.serve())
    yield

    try:
        task.cancel()
        await task
    except asyncio.CancelledError:
        ...


app = FastAPI(lifespan=lifespan)
app.include_router(make_fastapi_router(clock_app))

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app)
