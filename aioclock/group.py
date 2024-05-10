import asyncio
from functools import wraps
from typing import Any, Callable, Union

from fast_depends import inject

from aioclock.provider import get_provider
from aioclock.task import Task
from aioclock.triggers import BaseTrigger


class Group:
    def __init__(self, *, tasks: Union[list[Task], None] = None):
        """
        Group of tasks that will be run together.

        Best use case is to have a good modularity and separation of concerns.
        For example, you can have a group of tasks that are responsible for sending emails.
        And another group of tasks that are responsible for sending notifications.

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
        self._tasks: list[Task] = tasks or []

    def task(self, *, trigger: BaseTrigger):
        """Function used to decorate tasks, to be registered inside AioClock.

        Example:
        ```python
        from aioclock import Group, Forever
        @group.task(trigger=Forever())
        async def send_email():
            ...
        ```
        """

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
