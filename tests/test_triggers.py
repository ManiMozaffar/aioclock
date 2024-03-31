from datetime import datetime

import pytz

from aioclock.triggers import At


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
            tzinfo=pytz.timezone("Europe/Istanbul"),
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
            tzinfo=pytz.timezone("Europe/Istanbul"),
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
            tzinfo=pytz.timezone("Europe/Istanbul"),
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
            tzinfo=pytz.timezone("Europe/Istanbul"),
        )
    )
    assert val == 518400
