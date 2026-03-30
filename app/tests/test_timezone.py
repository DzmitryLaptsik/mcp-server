import pytest

from tools.timezone import (
    TimezoneConvertInput,
    TimezoneConvertOutput,
    WorldTimeInput,
    WorldTimeOutput,
    convert_timezone,
    get_world_time,
)


def test_get_world_time_utc():
    result = get_world_time(WorldTimeInput(timezone="UTC"))
    assert isinstance(result, WorldTimeOutput)
    assert result.timezone == "UTC"
    assert result.utc_offset == "+00:00"


def test_get_world_time_tokyo():
    result = get_world_time(WorldTimeInput(timezone="Asia/Tokyo"))
    assert result.timezone == "Asia/Tokyo"
    assert result.utc_offset == "+09:00"


def test_get_world_time_invalid_timezone_raises():
    with pytest.raises(Exception):
        get_world_time(WorldTimeInput(timezone="Invalid/Zone"))


def test_convert_timezone_single_target():
    result = convert_timezone(TimezoneConvertInput(
        time="15:00",
        date="2026-03-30",
        source_timezone="America/New_York",
        target_timezones=["Europe/London"],
    ))

    assert isinstance(result, TimezoneConvertOutput)
    assert result.source.timezone == "America/New_York"
    assert len(result.targets) == 1
    assert result.targets[0].timezone == "Europe/London"
    # EDT is UTC-4, BST is UTC+1 in March, so 15:00 EDT = 20:00 BST
    assert "20:00:00" in result.targets[0].datetime


def test_convert_timezone_multiple_targets():
    result = convert_timezone(TimezoneConvertInput(
        time="12:00",
        date="2026-01-15",
        source_timezone="UTC",
        target_timezones=["Asia/Tokyo", "America/Los_Angeles"],
    ))

    assert len(result.targets) == 2
    tokyo = result.targets[0]
    la = result.targets[1]
    # UTC 12:00 = Tokyo 21:00 (UTC+9), LA 04:00 (UTC-8 in January)
    assert "21:00:00" in tokyo.datetime
    assert "04:00:00" in la.datetime


def test_convert_timezone_defaults_date_to_today():
    result = convert_timezone(TimezoneConvertInput(
        time="10:00",
        source_timezone="UTC",
        target_timezones=["UTC"],
    ))
    assert "10:00:00" in result.source.datetime
    assert "10:00:00" in result.targets[0].datetime
