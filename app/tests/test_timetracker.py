import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, AsyncMock

from tools.timetracker.schemas import (
    ActiveTimersOutput,
    ListTimeEntriesInput,
    ListTimeEntriesOutput,
    TimeSummaryInput,
    TimeSummaryOutput,
    TrackAction,
    TrackTimeInput,
    TrackTimeOutput,
)
from tools.timetracker.service import TimeTrackerService


@pytest.fixture
def timetracker_service(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test_timetracker.db")
    monkeypatch.setattr("tools.timetracker.service.settings.TIMETRACKER_DB_PATH", db_path)
    return TimeTrackerService()


async def test_start_tracking(timetracker_service: TimeTrackerService):
    result = await timetracker_service.track_time(
        TrackTimeInput(action=TrackAction.START, project="landing page")
    )
    assert isinstance(result, TrackTimeOutput)
    assert result.action == "start"
    assert "Started" in result.message


async def test_start_already_running(timetracker_service: TimeTrackerService):
    await timetracker_service.track_time(TrackTimeInput(action=TrackAction.START, project="landing page"))
    result = await timetracker_service.track_time(TrackTimeInput(action=TrackAction.START, project="landing page"))
    assert "already running" in result.message


async def test_stop_tracking(timetracker_service: TimeTrackerService):
    await timetracker_service.track_time(TrackTimeInput(action=TrackAction.START, project="api work"))
    result = await timetracker_service.track_time(TrackTimeInput(action=TrackAction.STOP, project="api work"))
    assert result.action == "stop"
    assert "Stopped" in result.message
    assert result.duration is not None


async def test_stop_no_running_timer(timetracker_service: TimeTrackerService):
    result = await timetracker_service.track_time(TrackTimeInput(action=TrackAction.STOP, project="nothing"))
    assert "No running timer" in result.message


async def test_multiple_projects_independent(timetracker_service: TimeTrackerService):
    """Starting a timer on one project doesn't affect another."""
    await timetracker_service.track_time(TrackTimeInput(action=TrackAction.START, project="Project A"))
    await timetracker_service.track_time(TrackTimeInput(action=TrackAction.START, project="Project B"))

    stop_a = await timetracker_service.track_time(TrackTimeInput(action=TrackAction.STOP, project="Project A"))
    stop_b = await timetracker_service.track_time(TrackTimeInput(action=TrackAction.STOP, project="Project B"))

    assert "Stopped" in stop_a.message
    assert "Stopped" in stop_b.message


async def test_get_time_summary(timetracker_service: TimeTrackerService):
    """Summary aggregates completed entries per project."""
    # Use the service to create entries, then manipulate timestamps for predictable durations
    import aiosqlite

    now = datetime.now(timezone.utc)
    two_hours_ago = now - timedelta(hours=2)
    one_hour_ago = now - timedelta(hours=1)

    # Start and stop via service to create the table, then update timestamps
    await timetracker_service.track_time(TrackTimeInput(action=TrackAction.START, project="Project A"))
    await timetracker_service.track_time(TrackTimeInput(action=TrackAction.STOP, project="Project A"))
    await timetracker_service.track_time(TrackTimeInput(action=TrackAction.START, project="Project B"))
    await timetracker_service.track_time(TrackTimeInput(action=TrackAction.STOP, project="Project B"))

    # Override timestamps for predictable durations
    async with aiosqlite.connect(timetracker_service.db_path) as db:
        await db.execute(
            "UPDATE time_entries SET started_at = ?, stopped_at = ? WHERE id = 1",
            (two_hours_ago.isoformat(), one_hour_ago.isoformat()),
        )
        await db.execute(
            "UPDATE time_entries SET started_at = ?, stopped_at = ? WHERE id = 2",
            (one_hour_ago.isoformat(), now.isoformat()),
        )
        await db.commit()

    result = await timetracker_service.get_time_summary(TimeSummaryInput())
    assert isinstance(result, TimeSummaryOutput)
    assert len(result.projects) == 2
    assert result.total_minutes >= 118  # ~2 hours total, allow rounding


# --- list_active_timers ---

async def test_list_active_timers_empty(timetracker_service: TimeTrackerService):
    result = await timetracker_service.list_active_timers()
    assert isinstance(result, ActiveTimersOutput)
    assert result.total == 0
    assert result.timers == []


async def test_list_active_timers_shows_running(timetracker_service: TimeTrackerService):
    await timetracker_service.track_time(TrackTimeInput(action=TrackAction.START, project="Project A"))
    await timetracker_service.track_time(TrackTimeInput(action=TrackAction.START, project="Project B"))

    result = await timetracker_service.list_active_timers()
    assert result.total == 2
    projects = [t.project for t in result.timers]
    assert "Project A" in projects
    assert "Project B" in projects


async def test_list_active_timers_excludes_stopped(timetracker_service: TimeTrackerService):
    await timetracker_service.track_time(TrackTimeInput(action=TrackAction.START, project="Done"))
    await timetracker_service.track_time(TrackTimeInput(action=TrackAction.STOP, project="Done"))
    await timetracker_service.track_time(TrackTimeInput(action=TrackAction.START, project="Running"))

    result = await timetracker_service.list_active_timers()
    assert result.total == 1
    assert result.timers[0].project == "Running"
    assert result.total_completed_sessions == 1


# --- list_time_entries ---

async def test_list_time_entries_shows_all(timetracker_service: TimeTrackerService):
    await timetracker_service.track_time(TrackTimeInput(action=TrackAction.START, project="A"))
    await timetracker_service.track_time(TrackTimeInput(action=TrackAction.STOP, project="A"))
    await timetracker_service.track_time(TrackTimeInput(action=TrackAction.START, project="B"))

    result = await timetracker_service.list_time_entries(ListTimeEntriesInput())
    assert isinstance(result, ListTimeEntriesOutput)
    assert result.total == 2
    assert result.entries[0].status == "running"  # most recent first
    assert result.entries[1].status == "completed"


async def test_list_time_entries_filter_by_project(timetracker_service: TimeTrackerService):
    await timetracker_service.track_time(TrackTimeInput(action=TrackAction.START, project="A"))
    await timetracker_service.track_time(TrackTimeInput(action=TrackAction.STOP, project="A"))
    await timetracker_service.track_time(TrackTimeInput(action=TrackAction.START, project="B"))
    await timetracker_service.track_time(TrackTimeInput(action=TrackAction.STOP, project="B"))

    result = await timetracker_service.list_time_entries(ListTimeEntriesInput(project="A"))
    assert result.total == 1
    assert result.entries[0].project == "A"
