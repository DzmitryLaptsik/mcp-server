from tools import mcp
from tools.timetracker.schemas import TimeSummaryInput, TrackTimeInput
from tools.timetracker.service import TimeTrackerService

_timetracker_service = None


def _get_timetracker_service() -> TimeTrackerService:
    global _timetracker_service
    if _timetracker_service is None:
        _timetracker_service = TimeTrackerService()
    return _timetracker_service


@mcp.tool(description="Start or stop tracking time on a project. Use action='start' to begin and action='stop' to end. Logs the duration automatically.")
async def track_time(input: TrackTimeInput):
    return await _get_timetracker_service().track_time(input)


@mcp.tool(description="Get a summary of tracked time by project for a date range. Defaults to the current week. Shows per-project and total hours.")
async def get_time_summary(input: TimeSummaryInput):
    return await _get_timetracker_service().get_time_summary(input)
