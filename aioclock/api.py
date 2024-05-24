"""
External API of the aioclock package, that can be used to interact with the AioClock instance.
This module could be very useful if you intend to use aioclock in a web application or a CLI tool.

Other tools and extension are written from this tool.

!!! danger "Note when writing to aioclock API and changing its state."
    Right now the state of AioClock instance is on the memory level, so if you write an API and change a task's trigger time, it will not persist.
    In future we might store the state of AioClock instance in a database, so that it always remains same.
    But this is a bit tricky and implicit because then your code gets ignored and database is preferred over the database.
    For now you may consider it as a way to change something without redeploying the application, but it is not very recommended to write.
"""

import sys
from typing import Any, Awaitable, Callable, TypeVar, Union
from uuid import UUID

from fast_depends import inject
from pydantic import BaseModel

from aioclock.app import AioClock
from aioclock.exceptions import TaskIdNotFound
from aioclock.provider import get_provider
from aioclock.triggers import TriggerT

if sys.version_info < (3, 10):
    from typing_extensions import ParamSpec
else:
    from typing import ParamSpec

T = TypeVar("T")
P = ParamSpec("P")


class TaskMetadata(BaseModel):
    """Metadata of the task that is included in the AioClock instance.

    Attributes:
        id: UUID: Task ID that is unique for each task, and changes every time you run the aioclock app.
            In future we might store task ID in a database, so that it always remains same.
        trigger: Union[TriggerT, Any]: Trigger that is used to run the task, type is also any to ease implementing new triggers.
        task_name: str: Name of the task function.
    """

    id: UUID

    trigger: Union[TriggerT, Any]

    task_name: str


async def run_specific_task(task_id: UUID, app: AioClock):
    """Run a specific task immediately by its ID, from the AioClock instance.

    Example:
        ```python
        from aioclock import  AioClock, Once
        from aioclock.api import run_specific_task

        app = AioClock()

        @app.task(trigger=Once())
        async def main():
            print("Hello World")

        async def some_other_func():
            await run_specific_task(app._tasks[0].id, app)
        ```

    """
    task = next((task for task in app._tasks if task.id == task_id), None)
    if not task:
        raise TaskIdNotFound
    return await run_with_injected_deps(task.func)


async def run_with_injected_deps(func: Callable[P, Awaitable[T]]) -> T:
    """Runs an aioclock decorated function, with all the dependencies injected.

    Example:
        ```python
        from aioclock import Once, AioClock, Depends
        from aioclock.api import run_with_injected_deps

        app = AioClock()

        def some_dependency():
            return 1

        @app.task(trigger=Once())
        async def main(bar: int = Depends(some_dependency)):
            print("Hello World")
            return bar

        async def some_other_func():
            foo = await run_with_injected_deps(main)
            assert foo == 1
        ```

    """
    return await inject(func, dependency_overrides_provider=get_provider())()  # type: ignore


async def get_metadata_of_all_tasks(app: AioClock) -> list[TaskMetadata]:
    """Get metadata of all tasks that are included in the AioClock instance.

    Example:
        ```python
        from aioclock import AioClock, Once
        from aioclock.api import get_metadata_of_all_tasks

        app = AioClock()
        @app.task(trigger=Once())
        async def main(): ...

        metadata = await get_metadata_of_all_tasks(app)
        ```
    """
    return [
        TaskMetadata(
            id=task.id,
            trigger=task.trigger,
            task_name=task.func.__name__,
        )
        for task in app._get_tasks(exclude_type=set())
    ]
