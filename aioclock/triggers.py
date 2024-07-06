"""
Triggers are used to determine when the event should be triggered. It can be based on time, or some other condition.
You can create custom triggers by inheriting from `BaseTrigger` class.

!!! info "Don't run CPU intensitve or thread-block IO task "
    AioClock's trigger are all running in async, only on one CPU.
    So, if you run a CPU intensive task, or a task that blocks the thread, then it will block the entire event loop.
    If you have a sync IO task, then it's recommended to use `run_in_executor` to run the task in a separate thread.
    Or use similiar libraries like `asyncer` or `trio` to run the task in a separate thread.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from copy import deepcopy
from datetime import datetime, timedelta
from typing import Annotated, Generic, Literal, TypeVar, Union

import zoneinfo
from annotated_types import Interval
from croniter import croniter
from dateutil.relativedelta import relativedelta
from pydantic import BaseModel, Field, PositiveInt, model_validator

from aioclock.custom_types import PositiveNumber, Triggers

TriggerTypeT = TypeVar("TriggerTypeT")


WEEKDAY_MAPPER: dict[
    Literal[
        "every monday",
        "every tuesday",
        "every wednesday",
        "every thursday",
        "every friday",
        "every saturday",
        "every sunday",
        "every day",
    ],
    int,
] = {
    "every monday": 0,
    "every tuesday": 1,
    "every wednesday": 2,
    "every thursday": 3,
    "every friday": 4,
    "every saturday": 5,
    "every sunday": 6,
}


class BaseTrigger(BaseModel, ABC, Generic[TriggerTypeT]):
    """
    Base class for all triggers.
    A trigger is a way to determine when the event should be triggered. It can be based on time, or some other condition.


    The way trigger are used is as follows:
        1. An async function which is a task, is decorated with framework, and trigger is the arguement for the decorator
        2. `get_waiting_time_till_next_trigger` is called to get the time in seconds, after which the event should be triggered.
        3. If the time is not None, then it logs the time that is predicted for the event to be triggered.
        4. `trigger_next` is called immidiately after that, which triggers the event.

    You can create trigger by yourself, by inheriting from `BaseTrigger` class.

    Example:
        ```python
        from aioclock.triggers import BaseTrigger
        from typing import Literal

        class Forever(BaseTrigger[Literal["Forever"]]):
            type_: Literal["Forever"] = "Forever"

            def should_trigger(self) -> bool:
                return True

            async def trigger_next(self) -> None:
                return None

            async def get_waiting_time_till_next_trigger(self):
                if self.should_trigger():
                    return 0
                return None
        ```

    Attributes:
        type_: Type of the trigger. It is a string, which is used to identify the trigger's name.
            You can change the type by using `Generic` type when inheriting from `BaseTrigger`.

        expected_trigger_time: Expected time when the event should be triggered. This gets updated
            by Task Runner. It can be used on API layer, to know when the event is expected to be triggered.
    """

    type_: TriggerTypeT

    expected_trigger_time: Union[datetime, None] = None

    @abstractmethod
    async def trigger_next(self) -> None:
        """
        `trigger_next` keep track of the event, and triggers the event.
        The function shall return when the event is triggered and should be executed.
        """

    def should_trigger(self) -> bool:
        """
        `should_trigger` checks if the event should be triggered or not.
        If not, then the event will not be triggered anymore.
        You can save the state of the trigger and task inside the instance, and then check if the event should be triggered or not.
        For instance, in `LoopCounter` trigger, it keeps track of the number of times the event has been triggered,
        and then checks if the event should be triggered or not.
        """
        return True

    @abstractmethod
    async def get_waiting_time_till_next_trigger(self) -> Union[float, None]:
        """
        Returns the time in seconds, after which the event should be triggered.
        Returns None, if the event should not trigger anymore.
        """
        ...


class Forever(BaseTrigger[Literal[Triggers.FOREVER]]):
    """A trigger that is always triggered imidiately.

    Example:
        ```python

            from aioclock import AioClock, Forever

            app = AioClock()

            # instead of this:
            async def my_task():
                while True:
                    try:
                        await asyncio.sleep(3)
                        1/0
                    except DivisionByZero:
                        pass

            # use this:
            @app.task(trigger=Forever())
            async def my_task():
                await asyncio.sleep(3)
                1/0
        ```

    Attributes:
        type_: Type of the trigger. It is a string, which is used to identify the trigger's name.
            You can change the type by using `Generic` type when inheriting from `BaseTrigger`.

    """

    type_: Literal[Triggers.FOREVER] = Triggers.FOREVER

    def should_trigger(self) -> bool:
        return True

    async def trigger_next(self) -> None:
        return None

    async def get_waiting_time_till_next_trigger(self):
        return 0


class LoopController(BaseTrigger, ABC, Generic[TriggerTypeT]):
    """
    Base class for all triggers that have loop control.

    Attributes:
        type_: Type of the trigger. It is a string, which is used to identify the trigger's name.
            You can change the type by using `Generic` type when inheriting from `LoopController`.

        max_loop_count: The maximum number of times the event should be triggered.
            If set to 3, then 4th time the event will not be triggered.
            If set to None, it will keep running forever.
            This is available for all triggers that inherit from `LoopController`.

        _current_loop_count: Current loop count, which is used to keep track of the number of times the event has been triggered.
            Private attribute, should not be accessed directly.
            This is available for all triggers that inherit from `LoopController`.
    """

    type_: TriggerTypeT
    _current_loop_count: int = 0
    max_loop_count: Union[PositiveInt, None] = None

    @model_validator(mode="after")
    def validate_loop_controll(self):
        if "_current_loop_count" in self.model_fields_set:
            raise ValueError("_current_loop_count is a private attribute, should not be provided.")
        return self

    def _increment_loop_counter(self) -> None:
        self._current_loop_count += 1

    def should_trigger(self) -> bool:
        if self.max_loop_count is None:
            return True
        if self.max_loop_count > self._current_loop_count:
            return True
        return False

    async def get_waiting_time_till_next_trigger(self):
        return 0


class Once(LoopController[Literal[Triggers.ONCE]]):
    """A trigger that is triggered only once. It is used to trigger the event only once, and then stop.

    Example:
        ```python
        from aioclock import AioClock, Once
        app = AioClock()

        app.task(trigger=Once())
        async def task():
            print("Hello World!")
        ```
    """

    type_: Literal[Triggers.ONCE] = Triggers.ONCE
    max_loop_count: Literal[1] = 1

    async def trigger_next(self) -> None:
        self._increment_loop_counter()
        return None

    async def get_waiting_time_till_next_trigger(self):
        if self._current_loop_count == 0:
            return 0
        return None


class OnStartUp(LoopController[Literal[Triggers.ON_START_UP]]):
    """Just like Once, but it triggers the event only once, when the application starts up.

    Example:
        ```python
        from aioclock import AioClock, OnStartUp
        app = AioClock()

        app.task(trigger=OnStartUp())
        async def task():
            print("Hello World!")
        ```
    """

    type_: Literal[Triggers.ON_START_UP] = Triggers.ON_START_UP
    max_loop_count: Literal[1] = 1

    async def trigger_next(self) -> None:
        self._increment_loop_counter()
        return None

    async def get_waiting_time_till_next_trigger(self):
        if self._current_loop_count == 0:
            return 0
        return None


class OnShutDown(LoopController[Literal[Triggers.ON_SHUT_DOWN]]):
    """Just like Once, but it triggers the event only once, when the application shuts down.

    Example:
        ```python
        from aioclock import AioClock, OnShutDown
        app = AioClock()

        app.task(trigger=OnShutDown())
        async def task():
            print("Hello World!")
        ```
    """

    type_: Literal[Triggers.ON_SHUT_DOWN] = Triggers.ON_SHUT_DOWN
    max_loop_count: Literal[1] = 1

    async def trigger_next(self) -> None:
        self._increment_loop_counter()
        return None

    async def get_waiting_time_till_next_trigger(self):
        if self._current_loop_count == 0:
            return 0
        return None


class Every(LoopController[Literal[Triggers.EVERY]]):
    """A trigger that is triggered every x time units.

    Example:
        ```python
        from aioclock import AioClock, Every
        app = AioClock()

        app.task(trigger=Every(seconds=3))
        async def task():
            print("Hello World!")
        ```

    Attributes:
        first_run_strategy: Strategy to use for the first run.
            If `immediate`, then the event will be triggered immediately,
                and then wait for the time to trigger the event again.
            If `wait`, then the event will wait for the time to trigger the event for the first time.

        seconds: Seconds to wait before triggering the event.
        minutes: Minutes to wait before triggering the event.
        hours: Hours to wait before triggering the event.
        days: Days to wait before triggering the event.
        weeks: Weeks to wait before triggering the event.

        max_loop_count: The maximum number of times the event should be triggered.
            If set to 3, then 4th time the event will not be triggered.
            If set to None, it will keep running forever.
            This is available for all triggers that inherit from `LoopController`.

    """

    type_: Literal[Triggers.EVERY] = Triggers.EVERY
    first_run_strategy: Literal["immediate", "wait"] = "wait"
    seconds: Union[PositiveNumber, None] = None
    minutes: Union[PositiveNumber, None] = None
    hours: Union[PositiveNumber, None] = None
    days: Union[PositiveNumber, None] = None
    weeks: Union[PositiveNumber, None] = None
    max_loop_count: Union[PositiveInt, None] = None

    @model_validator(mode="after")
    def validate_time_units(self):
        if (
            self.seconds is None
            and self.minutes is None
            and self.hours is None
            and self.days is None
            and self.weeks is None
        ):
            raise ValueError("At least one time unit must be provided.")

        return self

    @property
    def to_seconds(self) -> float:
        result = self.seconds or 0
        if self.weeks is not None:
            result += self.weeks * 604800
        if self.days is not None:
            result += self.days * 86400
        if self.hours is not None:
            result += self.hours * 3600
        if self.minutes is not None:
            result += self.minutes * 60

        return result

    async def trigger_next(self) -> None:
        self._increment_loop_counter()
        if self._current_loop_count == 1 and self.first_run_strategy == "immediate":
            return None
        await asyncio.sleep(self.to_seconds)
        return None

    async def get_waiting_time_till_next_trigger(self):
        # not incremented yet, so the counter is 0
        if self._current_loop_count == 0 and self.first_run_strategy == "immediate":
            return 0

        if self.should_trigger():
            return self.to_seconds
        return None


WEEK_TO_SECOND = 604800


class At(LoopController[Literal[Triggers.AT]]):
    """A trigger that is triggered at a specific time.

    Example:
        ```python

        from aioclock import AioClock, At

        app = AioClock()

        @app.task(trigger=At(hour=12, minute=30, tz="Asia/Kolkata"))
        async def task():
            print("Hello World!")
        ```

    Attributes:
        second: Second to trigger the event.
        minute: Minute to trigger the event.
        hour: Hour to trigger the event.
        at: Day of week to trigger the event. You would get the in-line typing support when using the trigger.
        tz: Timezone to use for the event.

        max_loop_count: The maximum number of times the event should be triggered.
            If set to 3, then 4th time the event will not be triggered.
            If set to None, it will keep running forever.
            This is available for all triggers that inherit from `LoopController`.


    """

    type_: Literal[Triggers.AT] = Triggers.AT
    max_loop_count: Union[PositiveInt, None] = None
    second: Annotated[int, Interval(ge=0, le=59)] = 0
    minute: Annotated[int, Interval(ge=0, le=59)] = 0
    hour: Annotated[int, Interval(ge=0, le=24)] = 0
    at: Literal[
        "every monday",
        "every tuesday",
        "every wednesday",
        "every thursday",
        "every friday",
        "every saturday",
        "every sunday",
        "every day",
    ] = "every day"
    tz: str

    @model_validator(mode="after")
    def validate_time_units(self):
        if self.second is None and self.minute is None and self.hour is None:
            raise ValueError("At least one time unit must be provided.")

        if self.tz is not None:
            try:
                zoneinfo.ZoneInfo(self.tz)
            except Exception as error:
                raise ValueError(f"Invalid timezone provided: {error}")

        return self

    def _shift_to_declared_weekday(self, target_time: datetime, tz_aware_now: datetime):
        if self.at == "every day":
            if tz_aware_now > target_time:  # if the time is already passed, then shift to next day
                target_time += timedelta(days=1)
            return target_time

        target_weekday: int = WEEKDAY_MAPPER[self.at]
        if tz_aware_now > target_time:  # if the time is already passed, then shift to next week
            return target_time + relativedelta(weeks=1)

        days_ahead = abs(target_weekday - tz_aware_now.weekday())
        return target_time + timedelta(days_ahead)

    def _get_next_ts(self, now: datetime) -> float:
        target_time = deepcopy(now).replace(
            hour=self.hour, minute=self.minute, second=self.second, microsecond=0
        )
        target_time = self._shift_to_declared_weekday(target_time, now)
        return (target_time - now).total_seconds()

    async def get_waiting_time_till_next_trigger(self, now: Union[datetime, None] = None):
        if now is None:
            now = datetime.now(tz=zoneinfo.ZoneInfo(self.tz))

        sleep_for = self._get_next_ts(now)
        return sleep_for

    async def trigger_next(self) -> None:
        self._increment_loop_counter()
        await asyncio.sleep(await self.get_waiting_time_till_next_trigger())


class Cron(LoopController[Literal[Triggers.CRON]]):
    """A trigger that is triggered at a specific time, using cron job format.
    If you are not familiar with the cron format, you may read about in [this wikipedia article](https://en.wikipedia.org/wiki/Cron).
    Or if you need an online tool to generate cron job, you may use [crontab.guru](https://crontab.guru/).

    Example:
        ```python
        from aioclock import AioClock, Cron

        app = AioClock()

        @app.task(trigger=Cron(cron="0 12 * * *", tz="Asia/Kolkata"))
        async def task():
            print("Hello World!")
        ```

    Attributes:
        cron: Cron job format to trigger the event.
        tz: Timezone to use for the event.

        max_loop_count: The maximum number of times the event should be triggered.
            If set to 3, then 4th time the event will not be triggered.
            If set to None, it will keep running forever.
            This is available for all triggers that inherit from `LoopController`.

    """

    type_: Literal[Triggers.CRON] = Triggers.CRON
    max_loop_count: Union[PositiveInt, None] = None
    cron: str
    tz: str

    @model_validator(mode="after")
    def validate_time_units(self):
        if self.tz is not None:
            try:
                zoneinfo.ZoneInfo(self.tz)
            except Exception as error:
                raise ValueError(f"Invalid timezone provided: {error}")

        if croniter.is_valid(self.cron) is False:
            raise ValueError("Invalid cron format provided.")
        return self

    async def get_waiting_time_till_next_trigger(self, now: Union[datetime, None] = None):
        if now is None:
            now = datetime.now(tz=zoneinfo.ZoneInfo(self.tz))

        cron_iter = croniter(self.cron, now)
        next_dt: datetime = cron_iter.get_next(datetime)
        return (next_dt - now).total_seconds()

    async def trigger_next(self) -> None:
        self._increment_loop_counter()
        await asyncio.sleep(await self.get_waiting_time_till_next_trigger())


class OrTrigger(LoopController[Literal[Triggers.OR]]):
    """
    A trigger that triggers the event if any of the inner triggers are met.

    Example:
        ```python
        from aioclock import AioClock, OrTrigger, Every, At

        app = AioClock()

        @app.task(trigger=OrTrigger(triggers=[Every(seconds=3), At(hour=12, minute=30, tz="Asia/Kolkata")]))
        async def task():
            print("Hello World!")
        ```

    Not that any trigger used with OrTrigger, is fully respected, hence if you have two trigger with `max_loop_count=1`,
        then each trigger will be triggered only once, and then stop, which result in the OrTrigger run only twice.
        Check example to understand this intended behaviour.

    Example:
        ```python
        from aioclock import AioClock, OrTrigger, Every, At

        app = AioClock()

        @app.task(trigger=OrTrigger( # this get triggered 20 times because :...
            triggers=[
                Every(seconds=3, max_loop_count=10), # will trigger the event 10 times
                At(hour=12, minute=30, tz="Asia/Kolkata", max_loop_count=10) # will trigger the event 10 times
            ]
        ))
        async def task():
            print("Hello World!")
        ```

    Attributes:
        triggers: List of triggers to use.
        max_loop_count: The maximum number of times the event should be triggered.
            If set to 3, then 4th time the event will not be triggered.
            If set to None, it will keep running forever.
            This is available for all triggers that inherit from `LoopController`.

    """

    type_: Literal[Triggers.OR] = Triggers.OR
    triggers: list[TriggerT]
    max_loop_count: Union[PositiveInt, None] = None

    def should_trigger(self) -> bool:
        all_triggers = {trigger.should_trigger() for trigger in self.triggers}
        if all_triggers == {False}:
            return False  # if all inner triggers should not trigger, then this shouldn't too.
        return super().should_trigger()

    async def find_closest_trigger(self) -> tuple[BaseTrigger, float | None]:
        triggers_with_next_trigger: list[tuple[BaseTrigger, float]] = []

        for trigger in self.triggers:
            if trigger.should_trigger():
                next_trigger = await trigger.get_waiting_time_till_next_trigger()
                if next_trigger is None:
                    # just return it as this should be executed immediately
                    return trigger, next_trigger
                triggers_with_next_trigger.append((trigger, next_trigger))

        return min(triggers_with_next_trigger, key=lambda x: x[1])

    async def trigger_next(self) -> None:
        self._increment_loop_counter()
        next_trigger, time_to_sleep = await self.find_closest_trigger()
        await next_trigger.trigger_next()
        if time_to_sleep is not None:
            await asyncio.sleep(time_to_sleep)
        return None

    async def get_waiting_time_till_next_trigger(self):
        _, to_sleep = await self.find_closest_trigger()
        return to_sleep


TriggerT = Annotated[
    Union[
        Forever,
        Once,
        Every,
        At,
        OnStartUp,
        OnShutDown,
        Cron,
        OrTrigger,
    ],
    Field(discriminator="type_"),
]
