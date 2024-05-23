import asyncio
import sys
from functools import wraps
from typing import Any, Awaitable, Callable, TypeVar

if sys.version_info < (3, 10):
    from typing_extensions import ParamSpec
else:
    from typing import ParamSpec

from fast_depends import inject

from aioclock.group import Group, Task
from aioclock.provider import get_provider
from aioclock.triggers import BaseTrigger
from aioclock.types import Triggers
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

    ```python
    from aioclock import AioClock, Once
    app = AioClock()

    # whatever next comes here
    await app.serve()
    ```

    """

    def __init__(self):
        """
        Initialize AioClock instance.
        No parameters are needed.
        """
        self._groups: list[Group] = []
        self._app_tasks: list[Task] = []

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
        """Decorator to add a task to the AioClock instance.

        Example:

        ```python
        from aioclock import AioClock, Once

        app = AioClock()

        @app.task(trigger=Once())
        async def main():
            print("Hello World")
        ```
        """

        def decorator(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
            @wraps(func)
            async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
                return await func(*args, **kwargs)

            self._app_tasks.append(
                Task(
                    func=inject(wrapper, dependency_overrides_provider=get_provider()),
                    trigger=trigger,
                )
            )
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

    def _get_tasks(self) -> list[Task]:
        return [
            task
            for task in self._tasks
            if task.trigger.type_ not in {Triggers.ON_START_UP, Triggers.ON_SHUT_DOWN}
        ]

    async def serve(self) -> None:
        """
        Serves AioClock
        Run the tasks in the right order.
        First, run the startup tasks, then run the tasks, and finally run the shutdown tasks.
        """

        self.include_group(Group(tasks=self._app_tasks))
        try:
            await asyncio.gather(
                *(task.run() for task in self._get_startup_task()), return_exceptions=False
            )

            await asyncio.gather(
                *(group.run() for group in self._get_tasks()), return_exceptions=False
            )
        finally:
            shutdown_tasks = self._get_shutdown_task()
            await asyncio.gather(*(task.run() for task in shutdown_tasks), return_exceptions=False)
