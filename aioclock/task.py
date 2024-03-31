from dataclasses import dataclass
from typing import Any, Callable

from aioclock.logger import logger
from aioclock.triggers import BaseTrigger


@dataclass
class Task:
    func: Callable[..., Any]
    trigger: BaseTrigger

    async def run(self):
        while self.trigger.should_trigger():
            try:
                await self.trigger.trigger_next()
                logger.debug(f"Running task {self.func.__name__}")
                await self.func()
            except Exception as error:
                logger.error(f"Error running task {self.func.__name__}: {error}")
