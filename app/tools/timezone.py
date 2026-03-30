from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field
from zoneinfo import ZoneInfo

from tools import mcp


class WorldTimeInput(BaseModel):
    timezone: str = Field(..., description="IANA timezone name, e.g. 'Asia/Tokyo', 'America/New_York'")


class WorldTimeOutput(BaseModel):
    timezone: str
    datetime: str = Field(..., description="Current date and time in the requested timezone")
    utc_offset: str = Field(..., description="UTC offset, e.g. '+09:00'")


class TimezoneConvertInput(BaseModel):
    time: str = Field(..., description="Time to convert in HH:MM format (24-hour)")
    date: Optional[str] = Field(None, description="Date in YYYY-MM-DD format. Defaults to today.")
    source_timezone: str = Field(..., description="Source IANA timezone, e.g. 'America/New_York'")
    target_timezones: list[str] = Field(..., description="List of target IANA timezones to convert to")


class ConvertedTime(BaseModel):
    timezone: str
    datetime: str
    utc_offset: str


class TimezoneConvertOutput(BaseModel):
    source: ConvertedTime
    targets: list[ConvertedTime]


@mcp.tool(description="Get the current time in any timezone. Useful for checking what time it is in another city or country.")
def get_world_time(input: WorldTimeInput) -> WorldTimeOutput:
    tz = ZoneInfo(input.timezone)
    now = datetime.now(tz)
    return WorldTimeOutput(
        timezone=input.timezone,
        datetime=now.strftime("%Y-%m-%d %H:%M:%S"),
        utc_offset=now.strftime("%z")[:3] + ":" + now.strftime("%z")[3:],
    )


@mcp.tool(description="Convert a time from one timezone to one or more target timezones. Great for scheduling across time zones.")
def convert_timezone(input: TimezoneConvertInput) -> TimezoneConvertOutput:
    source_tz = ZoneInfo(input.source_timezone)

    if input.date:
        date = datetime.strptime(input.date, "%Y-%m-%d").date()
    else:
        date = datetime.now(source_tz).date()

    hour, minute = map(int, input.time.split(":"))
    source_dt = datetime(date.year, date.month, date.day, hour, minute, tzinfo=source_tz)

    def _format(dt: datetime, tz_name: str) -> ConvertedTime:
        return ConvertedTime(
            timezone=tz_name,
            datetime=dt.strftime("%Y-%m-%d %H:%M:%S"),
            utc_offset=dt.strftime("%z")[:3] + ":" + dt.strftime("%z")[3:],
        )

    targets = []
    for tz_name in input.target_timezones:
        target_tz = ZoneInfo(tz_name)
        target_dt = source_dt.astimezone(target_tz)
        targets.append(_format(target_dt, tz_name))

    return TimezoneConvertOutput(
        source=_format(source_dt, input.source_timezone),
        targets=targets,
    )
