import asyncio
from functools import wraps
from typing import Any, Callable, Union

from fast_depends import inject

from aioclock.provider import get_provider
from aioclock.task import Task
from aioclock.triggers import BaseTrigger


class Group:
    def __init__(self, *, tasks: Union[list[Task], None] = None):
        self._tasks: list[Task] = tasks or []

    def task(self, *, trigger: BaseTrigger):
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            @wraps(func)
            async def wrapper(*args, **kwargs) -> Any:
                return await func(*args, **kwargs)

            self._tasks.append(
                Task(
                    func=inject(wrapper, dependency_overrides_provider=get_provider()),
                    trigger=trigger,
                )
            )
            return wrapper

        return decorator

    async def _run(self):
        """
        Just for purpose of being able to run all task in group
        Private method, should not be used outside of the library
        """
        await asyncio.gather(
            *(task.run() for task in self._tasks),
            return_exceptions=False,
        )
