import asyncio
from abc import ABC, abstractmethod
from copy import deepcopy
from datetime import datetime, timedelta
from typing import Literal, Union

import pytz
from pydantic import BaseModel, model_validator

from aioclock.types import EveryT, HourT, MinuteT, SecondT, Triggers


class BaseTrigger(BaseModel, ABC):
    type_: Triggers

    @abstractmethod
    async def trigger_next(self) -> None:
        """
        `trigger_next` keep waiting, until the event should be triggered.
        """

    def should_trigger(self) -> bool:
        return True


class Forever(BaseTrigger):
    type_: Literal[Triggers.FOREVER] = Triggers.FOREVER

    async def trigger_next(self) -> None:
        return None


class Once(BaseTrigger):
    type_: Literal[Triggers.ONCE] = Triggers.ONCE
    already_triggered: bool = False

    async def trigger_next(self) -> None:
        if self.already_triggered is False:
            self.already_triggered = True
            return None

        await asyncio.Event().wait()  # waits for ever


class OnStartUp(Once):
    type_: Literal[Triggers.ON_START_UP] = Triggers.ON_START_UP

    async def trigger_next(self) -> None:
        if self.already_triggered is False:
            self.already_triggered = True
            return None

    def should_trigger(self) -> bool:
        return not (self.already_triggered)


class OnShutDown(Once):
    type_: Literal[Triggers.ON_SHUT_DOWN] = Triggers.ON_SHUT_DOWN

    async def trigger_next(self) -> None:
        if self.already_triggered is False:
            self.already_triggered = True
            return None

    def should_trigger(self) -> bool:
        return not (self.already_triggered)


class Every(BaseTrigger):
    type_: Literal[Triggers.EVERY] = Triggers.EVERY

    seconds: Union[int, float, None] = None
    minutes: Union[int, float, None] = None
    hours: Union[int, float, None] = None
    days: Union[int, float, None] = None
    weeks: Union[int, float, None] = None

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
        await asyncio.sleep(self.to_seconds)
        return


WEEK_TO_SECOND = 604800


class At(BaseTrigger):
    type_: Literal[Triggers.AT] = Triggers.AT

    second: SecondT = 0
    minute: MinuteT = 0
    hour: HourT = 0
    at: EveryT = "every day"
    tz: str

    @model_validator(mode="after")
    def validate_time_units(self):
        if self.second is None and self.minute is None and self.hour is None:
            raise ValueError("At least one time unit must be provided.")

        if self.tz is not None:
            try:
                pytz.timezone(self.tz)
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
        if days_ahead == 7 and target_time.timestamp() - tz_aware_now.timestamp() < (error_margin):
            # date is today, and event is about to be triggered today. so no need to shift to 7 days.
            return target_time

        return target_time + timedelta(days_ahead)

    def _get_next_ts(self, now: datetime) -> float:
        target_time = deepcopy(now).replace(
            hour=self.hour, minute=self.minute, second=self.second, microsecond=0
        )
        target_time = self._shift_to_week(target_time, now)
        return (target_time - now).total_seconds()

    async def trigger_next(self) -> None:
        now = datetime.now(pytz.timezone(self.tz))
        sleep_for = self._get_next_ts(now)
        await asyncio.sleep(sleep_for)
