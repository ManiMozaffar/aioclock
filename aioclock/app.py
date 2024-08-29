"""
To initialize the AioClock instance, you need to import the AioClock class from the aioclock module.
AioClock class represent the aioclock, and handle the tasks and groups that will be run by the aioclock.

Another way to modularize your code is to use `Group` which is kinda the same idea as router in web frameworks.
"""

from __future__ import annotations

import asyncio
import sys
from functools import wraps
from typing import (
    Any,
    AsyncContextManager,
    Callable,
    ContextManager,
    Optional,
    TypeVar,
    Union,
)

import anyio

if sys.version_info < (3, 10):
    from typing_extensions import ParamSpec
else:
    from typing import ParamSpec

if sys.version_info < (3, 11):
    from typing_extensions import assert_never
else:
    from typing import assert_never

from asyncer import asyncify
from fast_depends import inject

from aioclock.custom_types import Triggers
from aioclock.group import Group, Task
from aioclock.provider import get_provider
from aioclock.triggers import BaseTrigger
from aioclock.utils import flatten_chain

T = TypeVar("T")
P = ParamSpec("P")


class AioClock:
    """
    AioClock is the main class that will be used to run the tasks.
    It will be responsible for running the tasks in the right order.

    Example:
        ```python
        from aioclock import AioClock, Once
        app = AioClock()

        @app.task(trigger=Once())
        async def main():
            print("Hello World")
        ```

    To run the aioclock final app simply do:

    Example:
        ```python
        from aioclock import AioClock, Once
        import asyncio

        app = AioClock()

        # whatever next comes here
        asyncio.run(app.serve())
        ```

    ## Lifespan

    You can define this startup and shutdown logic using the lifespan parameter of the AioClock instance.
    It should be as an  AsyncContextManager which get AioClock application as argument.
    You can find the example below.

    Example:
        ```python
            import asyncio
            from contextlib import asynccontextmanager

            from aioclock import AioClock

            ML_MODEL = [] # just some imaginary component that needs to be started and stopped


            @asynccontextmanager
            async def lifespan(app: AioClock):
                ML_MODEL.append(2)
                print("UP!")
                yield app
                ML_MODEL.clear()
                print("DOWN!")


            app = AioClock(lifespan=lifespan)


            if __name__ == "__main__":
                asyncio.run(app.serve())
        ```

    Here we are simulating the expensive startup operation of loading the model by putting the (fake)
    model function in the dictionary with machine learning models before the yield.
    This code will be executed before the application starts operating, during the startup.

    And then, right after the yield, we unload the model.
    This code will be executed after the application finishes handling requests, right before the shutdown.
    This could, for example, release resources like memory, a GPU or some database connection.

    It would also happen when you're stopping your application gracefully,
    for example, when you're shutting down your container.

    Lifespan could also be synchronous context manager. Check the example below.


    Example:
        ```python
            from contextlib import contextmanager

            from aioclock import AioClock

            ML_MODEL = []

            @contextmanager
            def lifespan_sync(sync_app: AioClock):
                ML_MODEL.append(2)
                print("UP!")
                yield sync_app
                ML_MODEL.clear()
                print("DOWN!")

            sync_app = AioClock(lifespan=lifespan_sync)

            if __name__ == "__main__":
                asyncio.run(app.serve())
        ```

    """

    def __init__(
        self,
        *,
        lifespan: Optional[
            Callable[[AioClock], AsyncContextManager[AioClock] | ContextManager[AioClock]]
        ] = None,
        limiter: Optional[anyio.CapacityLimiter] = None,
    ):
        """
        Initialize AioClock instance.
        No parameters are needed.

        Attributes:
            lifespan:
                A context manager that will be used to handle the startup and shutdown of the application.
                If not provided, the application will run without any startup and shutdown logic.
                To understand it better, check the examples and documentation above.

            limiter:
                Anyio CapacityLimiter. capacity limiter to use to limit the total amount of threads running
                Limiter that will be used to limit the number of tasks that are running at the same time.
                If not provided, it will fall back to the default limiter set on Application level.
                If no limiter is set on Application level, it will fall back to the default limiter set by AnyIO.

        """
        self._groups: list[Group] = []
        self._app_tasks: list[Task] = []
        self._limiter = limiter
        self.lifespan = lifespan

    _groups: list[Group]
    """List of groups that will be run by AioClock."""

    _app_tasks: list[Task]
    """List of tasks that will be run by AioClock."""

    @property
    def dependencies(self):
        """Dependencies provider that will be used to inject dependencies in tasks."""
        return get_provider()

    def override_dependencies(
        self, original: Callable[..., Any], override: Callable[..., Any]
    ) -> None:
        """Override a dependency with a new one.

        params:
            original:
                Original dependency that will be overridden.
            override:
                New dependency that will override the original one.

        Example:
            ```python
            from aioclock import AioClock

            def original_dependency():
                return 1

            def new_dependency():
                return 2

            app = AioClock()
            app.override_dependencies(original=original_dependency, override=new_dependency)
            ```

        """
        self.dependencies.override(original, override)

    def include_group(self, group: Group) -> None:
        """Include a group of tasks that will be run by AioClock.

        params:
            group:
                Group of tasks that will be run together.

        Example:
            ```python
            from aioclock import AioClock, Group, Once

            app = AioClock()

            group = Group()
            @group.task(trigger=Once())
            async def main():
                print("Hello World")

            app.include_group(group)
            ```
        """
        self._groups.append(group)
        return None

    def task(self, *, trigger: BaseTrigger, timeout: float | None = None):
        """
        Decorator to add a task to the AioClock instance.
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

            from aioclock import AioClock, Once

            app = AioClock()

            @app.task(trigger=Once())
            async def main():
                print("Hello World")
            ```

        Example:
            ```python

            from aioclock import AioClock, Once

            app = AioClock()

            @app.task(trigger=Once(), timeout=3)
            async def main():
                await some_io_task()
            ```
        """

        def decorator(func):
            @wraps(func)
            async def wrapped_function(*args, **kwargs):
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:  # run in threadpool to make sure it's not blocking the event loop
                    return await asyncify(func, limiter=self._limiter)(*args, **kwargs)

            self._app_tasks.append(
                Task(
                    func=inject(wrapped_function, dependency_overrides_provider=get_provider()),
                    trigger=trigger,
                    timeout=timeout,
                )
            )
            return wrapped_function

        return decorator

    @property
    def _tasks(self) -> list[Task]:
        result = flatten_chain([group._tasks for group in self._groups])
        return result

    def _get_shutdown_task(self) -> list[Task]:
        return [task for task in self._tasks if task.trigger.type_ == Triggers.ON_SHUT_DOWN]

    def _get_startup_task(self) -> list[Task]:
        return [task for task in self._tasks if task.trigger.type_ == Triggers.ON_START_UP]

    def _get_tasks(self, exclude_type: Union[set[Triggers], None] = None) -> list[Task]:
        exclude_type = (
            exclude_type
            if exclude_type is not None
            else {Triggers.ON_START_UP, Triggers.ON_SHUT_DOWN}
        )

        return [task for task in self._tasks if task.trigger.type_ not in exclude_type]

    async def serve(self) -> None:
        """
        Serves AioClock
        Run the tasks in the right order.
        First, run the startup tasks, then run the tasks, and finally run the shutdown tasks.
        """
        group = Group()
        group._tasks = self._app_tasks
        self.include_group(group)

        if self.lifespan is None:
            await self._run_tasks()
            return

        ctx = self.lifespan(self)

        if isinstance(ctx, AsyncContextManager):
            async with ctx:
                await self._run_tasks()

        elif isinstance(ctx, ContextManager):
            with ctx:
                await self._run_tasks()

        else:
            assert_never(ctx)

    async def _run_tasks(self) -> None:
        try:
            await asyncio.gather(
                *(task.run() for task in self._get_startup_task()), return_exceptions=False
            )

            await asyncio.gather(
                *(task.run() for task in self._get_tasks()), return_exceptions=False
            )
        finally:
            shutdown_tasks = self._get_shutdown_task()
            await asyncio.gather(*(task.run() for task in shutdown_tasks), return_exceptions=False)
