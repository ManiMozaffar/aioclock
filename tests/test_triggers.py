from datetime import datetime

import pytest
import zoneinfo

from aioclock.triggers import At, Cron, Every, Forever, LoopController, Once, OrTrigger


def test_at_trigger():
    # test this sunday
    trigger = At(at="every sunday", hour=14, minute=1, second=0, tz="Europe/Istanbul")

    val = trigger._get_next_ts(
        datetime(
            year=2024,
            month=3,
            day=31,
            hour=14,
            minute=00,
            second=0,
            tzinfo=zoneinfo.ZoneInfo("Europe/Istanbul"),
        )
    )
    assert val == 60

    # test next week
    trigger = At(at="every sunday", hour=14, second=59, tz="Europe/Istanbul")

    val = trigger._get_next_ts(
        datetime(
            year=2024,
            month=3,
            day=31,
            hour=14,
            minute=0,
            second=0,
            tzinfo=zoneinfo.ZoneInfo("Europe/Istanbul"),
        )
    )
    assert val == 59

    # test every day
    trigger = At(at="every day", hour=14, second=59, tz="Europe/Istanbul")
    val = trigger._get_next_ts(
        datetime(
            year=2024,
            month=3,
            day=31,
            hour=14,
            minute=0,
            second=0,
            tzinfo=zoneinfo.ZoneInfo("Europe/Istanbul"),
        )
    )
    assert val == 59

    # test next week
    trigger = At(at="every saturday", hour=14, second=0, tz="Europe/Istanbul")
    val = trigger._get_next_ts(
        datetime(
            year=2024,
            month=3,
            day=31,
            hour=14,
            minute=0,
            second=0,
            tzinfo=zoneinfo.ZoneInfo("Europe/Istanbul"),
        )
    )
    assert val == 518400


@pytest.mark.asyncio
async def test_loop_controller():
    # since once trigger is triggered, it should not trigger again.
    trigger = Once()
    assert trigger.should_trigger() is True
    await trigger.trigger_next()
    assert trigger.should_trigger() is False

    class IterateFiveTime(LoopController):
        type_: str = "foo"

        async def trigger_next(self) -> None:
            self._increment_loop_counter()
            return None

    trigger = IterateFiveTime(max_loop_count=5)
    for _ in range(5):
        assert trigger.should_trigger() is True
        await trigger.trigger_next()

    assert trigger.should_trigger() is False


@pytest.mark.asyncio
async def test_forever():
    trigger = Forever()
    assert trigger.should_trigger() is True
    await trigger.trigger_next()
    assert trigger.should_trigger() is True
    await trigger.trigger_next()
    assert trigger.should_trigger() is True


@pytest.mark.asyncio
async def test_every():
    # wait should always wait for the period on first run
    trigger = Every(seconds=1, first_run_strategy="wait")
    assert await trigger.get_waiting_time_till_next_trigger() == 1

    # immediate should always execute immediately, but wait for the period from second run.
    trigger = Every(seconds=1, first_run_strategy="immediate")
    assert await trigger.get_waiting_time_till_next_trigger() == 0
    trigger._increment_loop_counter()
    assert await trigger.get_waiting_time_till_next_trigger() == 1


@pytest.mark.asyncio
async def test_cron():
    # it's dumb idea to test library, but I don't trust it 100%, and i might drop it in the future.

    trigger = Cron(cron="* * * * *", tz="UTC")
    val = await trigger.get_waiting_time_till_next_trigger(
        datetime(
            year=2024,
            month=3,
            day=31,
            hour=14,
            minute=0,
            second=0,
            tzinfo=zoneinfo.ZoneInfo("UTC"),
        )
    )
    assert val == 60

    trigger = Cron(cron="2-10 * * * *", tz="UTC")
    assert (
        await trigger.get_waiting_time_till_next_trigger(
            datetime(
                year=2024,
                month=3,
                day=31,
                hour=11,
                minute=48,
                second=0,
                tzinfo=zoneinfo.ZoneInfo("Europe/Berlin"),
            )
        )
        == 14 * 60
    )

    with pytest.raises(ValueError):
        trigger = Cron(cron="* * * * 65", tz="UTC")


@pytest.mark.asyncio
async def test_or_trigger_state():
    trigger = OrTrigger(triggers=[Once(), Once()])
    assert trigger.should_trigger() is True
    await trigger.trigger_next()
    assert trigger.should_trigger() is True
    await trigger.trigger_next()
    assert trigger.should_trigger() is False


@pytest.mark.asyncio
async def test_or_trigger_next():
    trigger = OrTrigger(
        triggers=[Every(seconds=0, max_loop_count=2), Every(seconds=0, max_loop_count=2)]
    )
    for _ in range(4):
        assert trigger.should_trigger() is True
        assert (await trigger.get_waiting_time_till_next_trigger()) == 0
        await trigger.trigger_next()

    assert trigger.should_trigger() is False
