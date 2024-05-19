import asyncio
from abc import ABC, abstractmethod
from copy import deepcopy
from datetime import datetime, timedelta
from typing import Generic, Literal, TypeVar, Union

import zoneinfo
from pydantic import BaseModel, PositiveInt, model_validator

from aioclock.types import EveryT, HourT, MinuteT, PositiveNumber, SecondT, Triggers

TriggerTypeT = TypeVar("TriggerTypeT")


class BaseTrigger(BaseModel, ABC, Generic[TriggerTypeT]):
    """
    Base class for all triggers.
    A trigger is a way to determine when the event should be triggered. It can be based on time, or some other condition.


    The way trigger are used is as follows:
        1. An async function which is a task, is decorated with framework, and trigger is the arguement for the decorator
        2. `get_waiting_time_till_next_trigger` is called to get the time in seconds, after which the event should be triggered.
        3. If the time is not None, then it logs the time that is predicted for the event to be triggered.
        4. `trigger_next` is called immidiately after that, which triggers the event.

    This is an example to implement a custom trigger, by yourself:

    ```python
    from aioclock.triggers import BaseTrigger


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
    """

    type_: TriggerTypeT
    """
    Type of the trigger. It is a string, which is used to identify the trigger's name.
    You can change the type by using `Generic` type when inheriting from `BaseTrigger`.
    """

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

        from aioclock import AioClock,

        app = AioClock()

        # instead of this:
        async def my_task():
            while True:
                try:
                    await asyncio.sleep(3)
                    1/0
                excpet DivisionByZero:
                    pass

        # use this:
        @app.task(trigger=Forever())
        async def my_task():
            await asyncio.sleep(3)
            1/0
    ```
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
    """

    type_: TriggerTypeT
    """
    Type of the trigger. It is a string, which is used to identify the trigger's name.
    You can change the type by using `Generic` type when inheriting from `BaseTrigger`.
    """

    _current_loop_count: int = 0
    """
    Current loop count, which is used to keep track of the number of times the event has been triggered.
    Private attribute, should not be accessed directly.
    """

    max_loop_count: Union[PositiveInt, None] = None
    """
    The maximum number of times the event should be triggered.

    If set to 3, then 4th time the event will not be triggered.
    If set to None, it will keep running forever.

    This is available for all triggers that inherit from `LoopController`.
    """

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
        if self._current_loop_count < self.max_loop_count:
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
    max_loop_count: PositiveInt = 1
    """The maximum number of times the event should be triggered. Should be always 1 for this trigger"""

    async def trigger_next(self) -> None:
        self._increment_loop_counter()
        return None

    async def get_waiting_time_till_next_trigger(self):
        return 0


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
    max_loop_count: PositiveInt = 1
    """The maximum number of times the event should be triggered. Should be always 1 for this trigger."""

    async def trigger_next(self) -> None:
        self._increment_loop_counter()
        return None

    async def get_waiting_time_till_next_trigger(self):
        return 0


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
    max_loop_count: PositiveInt = 1
    """The maximum number of times the event should be triggered. Should be always 1 for this trigger."""

    async def trigger_next(self) -> None:
        self._increment_loop_counter()
        return None

    async def get_waiting_time_till_next_trigger(self):
        return 0


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

    """

    type_: Literal[Triggers.EVERY] = Triggers.EVERY

    first_run_strategy: Literal["immediate", "wait"] = "wait"
    """Strategy to use for the first run.
    If `immediate`, then the event will be triggered immediately,
        and then wait for the time to trigger the event again.
    If `wait`, then the event will wait for the time to trigger the event for the first time.
    """

    seconds: Union[PositiveNumber, None] = None
    """Seconds to wait before triggering the event."""

    minutes: Union[PositiveNumber, None] = None
    """Minutes to wait before triggering the event."""

    hours: Union[PositiveNumber, None] = None
    """Hours to wait before triggering the event."""

    days: Union[PositiveNumber, None] = None
    """Days to wait before triggering the event."""

    weeks: Union[PositiveNumber, None] = None
    """Weeks to wait before triggering the event."""

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
    """

    type_: Literal[Triggers.AT] = Triggers.AT

    second: SecondT = 0
    """Second to trigger the event."""

    minute: MinuteT = 0
    """Minute to trigger the event."""

    hour: HourT = 0
    """Hour to trigger the event."""

    at: EveryT = "every day"
    """Day of week to trigger the event. You would get the in-line typing support when using the trigger.
    """

    tz: str
    """Timzeon to use for the event."""

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

    def _shift_to_week(self, target_time: datetime, tz_aware_now: datetime):
        target_weekday: dict[EveryT, Union[int, None]] = {
            "every monday": 0,
            "every tuesday": 1,
            "every wednesday": 2,
            "every thursday": 3,
            "every friday": 4,
            "every saturday": 5,
            "every sunday": 6,
            "every day": None,
        }[self.at]

        if target_weekday is None:
            if target_time < tz_aware_now:
                target_time += timedelta(days=1)
            return target_time

        days_ahead = target_weekday - tz_aware_now.weekday()  # type: ignore
        if days_ahead <= 0:
            days_ahead += 7

        if self.at == "every day":
            target_time += timedelta(days=(1 if target_time < tz_aware_now else 0))
            return target_time

        # 1 second error
        error_margin = WEEK_TO_SECOND - 1
        if days_ahead == 7 and target_time.timestamp() - tz_aware_now.timestamp() < error_margin:
            # date is today, and event is about to be triggered today. so no need to shift to 7 days.
            return target_time

        return target_time + timedelta(days_ahead)

    def _get_next_ts(self, now: datetime) -> float:
        target_time = deepcopy(now).replace(
            hour=self.hour, minute=self.minute, second=self.second, microsecond=0
        )
        target_time = self._shift_to_week(target_time, now)
        return (target_time - now).total_seconds()

    def get_sleep_time(self):
        now = datetime.now(tz=zoneinfo.ZoneInfo(self.tz))
        sleep_for = self._get_next_ts(now)
        return sleep_for

    async def get_waiting_time_till_next_trigger(self):
        return self.get_sleep_time()

    async def trigger_next(self) -> None:
        self._increment_loop_counter()
        await asyncio.sleep(self.get_sleep_time())
