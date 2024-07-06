"""
To initialize the AioClock instance, you need to import the AioClock class from the aioclock module.
AioClock class represent the aioclock, and handle the tasks and groups that will be run by the aioclock.

Another way to modulize your code is to use `Group` which is kinda the same idea as router in web frameworks.
"""

import asyncio
import sys
from functools import wraps
from typing import Any, Callable, Optional, TypeVar, Union

import anyio

if sys.version_info < (3, 10):
    from typing_extensions import ParamSpec
else:
    from typing import ParamSpec

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

    """

    def __init__(self, limiter: Optional[anyio.CapacityLimiter] = None):
        """
        Initialize AioClock instance.
        No parameters are needed.

        Attributes:
            limiter:
                Anyio CapacityLimiter. capacity limiter to use to limit the total amount of threads running
                Limiter that will be used to limit the number of tasks that are running at the same time.
                If not provided, it will fallback to the default limiter set on Application level.
                If no limiter is set on Application level, it will fallback to the default limiter set by AnyIO.

        """
        self._groups: list[Group] = []
        self._app_tasks: list[Task] = []
        self._limiter = limiter

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

    def task(self, *, trigger: BaseTrigger):
        """
        Decorator to add a task to the AioClock instance.
        If decorated function is sync, aioclock will run it in a thread pool executor, using AnyIO.
        But if you try to run the decorated function, it will run in the same thread, blocking the event loop.
        It is intended to not change all your `sync functions` to coroutine functions,
            and they can be used outside of aioclock, if needed.

        params:
            trigger: BaseTrigger
                Trigger that will trigger the task to be running.

        Example:
            ```python

            from aioclock import AioClock, Once

            app = AioClock()

            @app.task(trigger=Once())
            async def main():
                print("Hello World")
            ```
        """

        def decorator(func):
            @wraps(func)
            async def wrapped_funciton(*args, **kwargs):
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:  # run in threadpool to make sure it's not blocking the event loop
                    return await asyncify(func, limiter=self._limiter)(*args, **kwargs)

            self._app_tasks.append(
                Task(
                    func=inject(wrapped_funciton, dependency_overrides_provider=get_provider()),
                    trigger=trigger,
                )
            )
            if asyncio.iscoroutinefunction(func):
                return wrapped_funciton
            else:

                @wraps(func)
                def wrapper(*args, **kwargs):
                    return func(*args, **kwargs)

                return wrapper

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
