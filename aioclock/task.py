"""
Aioclock wrap your functions with a task object, and append the task to the list of tasks in the AioClock instance.
After collecting all the tasks from decorated functions, aioclock serve them in order it has to be (startup, normal, shutdown).

These tasks keep running forever until the trigger's method `should_trigger` returns False.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, Awaitable, Callable
from uuid import UUID, uuid4

from aioclock.logger import logger
from aioclock.triggers import BaseTrigger


@dataclass
class Task:
    """Task that will be run by AioClock.
    Which always has a function and a trigger.
    This is internally used, when you decorate your function with `aioclock.task`.
    """

    func: Callable[..., Awaitable[Any]]
    """Decorated function that will be run by AioClock."""

    trigger: BaseTrigger
    """Trigger that will be used to run the function."""

    id: UUID = field(default_factory=uuid4)
    """
    Task ID that is unique for each task, and changes every time you run the aioclock app.
    In future we might store task ID in a database, so that it always remains same.
    """

    async def run(self):
        """
        Run the task, and handle the exceptions.
        If the task fails, log the error with exception, but keep running the tasks.
        """
        while self.trigger.should_trigger():
            try:
                next_trigger = await self.trigger.get_waiting_time_till_next_trigger()
                if next_trigger is not None:
                    logger.info(f"Triggering next task {self.func.__name__} in {next_trigger}")
                    self.trigger.expected_trigger_time = datetime.now(UTC) + timedelta(
                        seconds=next_trigger
                    )
                await self.trigger.trigger_next()
                logger.debug(f"Running task {self.func.__name__}")
                await self.func()
            except Exception as error:
                # Log the error, but keep running the tasks.
                # don't crash the whole application.
                logger.exception(f"Error running task {self.func.__name__}: {error}")

        self.trigger.expected_trigger_time = None
