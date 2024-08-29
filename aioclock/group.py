import asyncio
import sys
from functools import wraps
from typing import Optional, TypeVar

from asyncer import asyncify

if sys.version_info < (3, 10):
    from typing_extensions import ParamSpec
else:
    from typing import ParamSpec

import anyio
from fast_depends import inject

from aioclock.provider import get_provider
from aioclock.task import Task
from aioclock.triggers import BaseTrigger

T = TypeVar("T")
P = ParamSpec("P")


class Group:
    def __init__(
        self,
        *,
        limiter: Optional[anyio.CapacityLimiter] = None,
    ):
        """
        Group of tasks that will be run together.

        Best use case is to have a good modularity and separation of concerns.
        For example, you can have a group of tasks that are responsible for sending emails.
        And another group of tasks that are responsible for sending notifications.

        Params:
            limiter:
                Anyio CapacityLimiter. capacity limiter to use to limit the total amount of threads running
                Limiter that will be used to limit the number of tasks that are running at the same time.
                If not provided, it will fall back to the default limiter set on Application level.
                If no limiter is set on Application level, it will fall back to the default limiter set by AnyIO.

        Example:
            ```python

            from aioclock import Group, AioClock, Forever

            email_group = Group()

            # consider this as different file
            @email_group.task(trigger=Forever())
            async def send_email():
                ...

            # app.py
            aio_clock = AioClock()
            aio_clock.include_group(email_group)
            ```

        """
        self._tasks: list[Task] = []
        self._limiter = limiter

    def task(self, *, trigger: BaseTrigger, timeout: float | None = None):
        """
        Decorator to add a task to the group.
        If decorated function is sync, aioclock will run it in a thread pool executor, using AnyIO.
        But if you try to run the decorated function, it will run in the same thread, blocking the event loop.
        It is intended to not change all your `sync functions` to coroutine functions,
            and they can be used outside aioclock, if needed.

        params:
            trigger: BaseTrigger
                Trigger that will trigger the task to be running.

            timeout: float | None (defaults to None)
                Set a timeout for the task.
                If the task completion took longer than timeout,
                it will be cancelled and a `TaskTimeoutError` be raised by the Application.

        Example:
            ```python

            from aioclock import AioClock, Group, Once

            group = Group()

            @group.task(trigger=Once())
            async def main():
                print("Hello World")

            app = AioClock()
            app.include_group(group)
            ```

        Example:
            ```python

            from aioclock import AioClock, Group, Once

            group = Group()

            @group.task(trigger=Once(), timeout=4)
            async def main():
                print("Hello World")

            app = AioClock()
            app.include_group(group)
            ```
        """

        def decorator(func):
            @wraps(func)
            async def wrapped_function(*args, **kwargs):
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:  # run in threadpool to make sure it's not blocking the event loop
                    return await asyncify(func, limiter=self._limiter)(*args, **kwargs)

            self._tasks.append(
                Task(
                    func=inject(wrapped_function, dependency_overrides_provider=get_provider()),
                    trigger=trigger,
                    timeout=timeout,
                )
            )

            return wrapped_function

        return decorator

    async def _run(self):
        """
        Just for purpose of being able to run all task in group
        Private method, should not be used outside the library
        """
        await asyncio.gather(
            *(task.run() for task in self._tasks),
            return_exceptions=False,
        )
