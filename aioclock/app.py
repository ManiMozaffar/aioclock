import asyncio
from functools import wraps
from typing import Any, Callable

from fast_depends import inject

from aioclock.group import Group, Task
from aioclock.provider import get_provider
from aioclock.triggers import BaseTrigger
from aioclock.types import Triggers
from aioclock.utils import flatten_chain


class AioClock:
    def __init__(self):
        self._groups: list[Group] = []
        self._app_tasks: list[Task] = []

    @property
    def dependencies(self):
        return get_provider()

    def override_dependencies(
        self, original: Callable[..., Any], override: Callable[..., Any]
    ) -> None:
        self.dependencies.override(original, override)

    def include_group(self, group: Group) -> None:
        self._groups.append(group)
        return None

    def task(self, *, trigger: BaseTrigger):
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            @wraps(func)
            async def wrapper(*args, **kwargs) -> Any:
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
