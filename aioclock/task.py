from dataclasses import dataclass
from typing import Any, Callable

from aioclock.logger import logger
from aioclock.triggers import BaseTrigger


@dataclass
class Task:
    """Task that will be run by AioClock.
    Which always has a function and a trigger.
    This is internally used, when you decorate your function with `aioclock.task`.
    """

    func: Callable[..., Any]
    """Decorated function that will be run by AioClock."""

    trigger: BaseTrigger
    """Trigger that will be used to run the function."""

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
                await self.trigger.trigger_next()
                logger.debug(f"Running task {self.func.__name__}")
                await self.func()
            except Exception as error:
                # Log the error, but keep running the tasks.
                # don't crash the whole application.
                logger.exception(f"Error running task {self.func.__name__}: {error}")
