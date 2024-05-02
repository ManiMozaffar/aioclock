import asyncio
from abc import ABC, abstractmethod
from copy import deepcopy
from datetime import datetime, timedelta
from typing import Literal, Union

import zoneinfo
from pydantic import BaseModel, PositiveInt, model_validator

from aioclock.types import EveryT, HourT, MinuteT, PositiveNumber, SecondT, Triggers


class BaseTrigger(BaseModel, ABC):
    type_: Triggers

    @abstractmethod
    async def trigger_next(self) -> None:
        """
        `trigger_next` keep waiting, until the event should be triggered.
        """

    @abstractmethod
    def should_trigger(self) -> bool:
        """
        `should_trigger` checks if the event should be triggered or not.
        """
        return True

    @abstractmethod
    async def get_waiting_time_till_next_trigger(self) -> float | None:
        """
        `get_waiting_time_till_next_trigger` returns the time in seconds, after which the event should be triggered.
        Returns None, if the event should not trigger anymore.
        """
        ...


class Forever(BaseTrigger):
    type_: Literal[Triggers.FOREVER] = Triggers.FOREVER

    def should_trigger(self) -> bool:
        return True

    async def trigger_next(self) -> None:
        return None

    async def get_waiting_time_till_next_trigger(self):
        if self.should_trigger():
            return 0
        return None


class LoopController(BaseTrigger, ABC):
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
    """

    @model_validator(mode="after")
    def validate_loop_controll(self):
        if "_current_loop_count" in self.model_fields_set:
            raise ValueError("_current_loop_count is a private attribute, should not be provided.")
        return self

    def _increment_loop_counter(self) -> None:
        if self._current_loop_count is not None:
            self._current_loop_count += 1

    def should_trigger(self) -> bool:
        if self.max_loop_count is None:
            return True
        if self._current_loop_count < self.max_loop_count:
            return True
        return False

    async def get_waiting_time_till_next_trigger(self):
        if self.should_trigger():
            return 0
        return None


class Once(LoopController):
    type_: Literal[Triggers.ONCE] = Triggers.ONCE
    max_loop_count: PositiveInt = 1

    async def trigger_next(self) -> None:
        self._increment_loop_counter()
        return None

    async def get_waiting_time_till_next_trigger(self):
        if self.should_trigger():
            return 0
        return None


class OnStartUp(LoopController):
    type_: Literal[Triggers.ON_START_UP] = Triggers.ON_START_UP
    max_loop_count: PositiveInt = 1

    async def trigger_next(self) -> None:
        self._increment_loop_counter()
        return None

    async def get_waiting_time_till_next_trigger(self):
        if self.should_trigger():
            return 0
        return None


class OnShutDown(LoopController):
    type_: Literal[Triggers.ON_SHUT_DOWN] = Triggers.ON_SHUT_DOWN
    max_loop_count: PositiveInt = 1

    async def trigger_next(self) -> None:
        self._increment_loop_counter()
        return None

    async def get_waiting_time_till_next_trigger(self):
        if self.should_trigger():
            return 0
        return None


class Every(LoopController):
    type_: Literal[Triggers.EVERY] = Triggers.EVERY

    seconds: Union[PositiveNumber, None] = None
    minutes: Union[PositiveNumber, None] = None
    hours: Union[PositiveNumber, None] = None
    days: Union[PositiveNumber, None] = None
    weeks: Union[PositiveNumber, None] = None

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
        await asyncio.sleep(self.to_seconds)
        return

    async def get_waiting_time_till_next_trigger(self):
        if self.should_trigger():
            return self.to_seconds
        return None


WEEK_TO_SECOND = 604800


class At(LoopController):
    type_: Literal[Triggers.AT] = Triggers.AT

    second: SecondT = 0
    minute: MinuteT = 0
    hour: HourT = 0
    at: EveryT = "every day"
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
        if self.should_trigger():
            return self.get_sleep_time()
        return None

    async def trigger_next(self) -> None:
        self._increment_loop_counter()
        await asyncio.sleep(self.get_sleep_time())
