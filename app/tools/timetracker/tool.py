from mcp.types import ToolAnnotations

from tools import mcp
from tools.timetracker.schemas import (
    ActiveTimersOutput,
    ListTimeEntriesInput,
    ListTimeEntriesOutput,
    TimeSummaryInput,
    TimeSummaryOutput,
    TrackTimeInput,
    TrackTimeOutput,
)
from tools.timetracker.service import TimeTrackerService

_timetracker_service = None


def _get_timetracker_service() -> TimeTrackerService:
    global _timetracker_service
    if _timetracker_service is None:
        _timetracker_service = TimeTrackerService()
    return _timetracker_service


@mcp.tool(
    description="WRITE: Start or stop a time tracking timer. Only use when the user explicitly asks to start/stop tracking.",
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False),
)
async def track_time(input: TrackTimeInput) -> TrackTimeOutput:
    return await _get_timetracker_service().track_time(input)


@mcp.tool(
    description="READ: Show currently running timers. Use when user asks what timers are active or running.",
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def list_active_timers() -> ActiveTimersOutput:
    return await _get_timetracker_service().list_active_timers()


@mcp.tool(
    description="READ: Show individual time tracking sessions (both running and completed) with start/stop times and duration. Use when user asks to see their time entries, tracking history, or logged sessions.",
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def list_time_entries(input: ListTimeEntriesInput) -> ListTimeEntriesOutput:
    return await _get_timetracker_service().list_time_entries(input)


@mcp.tool(
    description="READ: Get an aggregated summary of tracked time by project for a date range. Use when the user asks how much total time was spent. Defaults to current week.",
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def get_time_summary(input: TimeSummaryInput) -> TimeSummaryOutput:
    return await _get_timetracker_service().get_time_summary(input)
