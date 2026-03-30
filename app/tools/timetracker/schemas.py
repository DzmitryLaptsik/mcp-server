from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class TrackAction(Enum):
    START = "start"
    STOP = "stop"


class TrackTimeInput(BaseModel):
    action: TrackAction = Field(..., description="'start' to begin tracking, 'stop' to end tracking")
    project: str = Field(..., max_length=200, description="Project name to track time for")


class TrackTimeOutput(BaseModel):
    action: str
    project: str
    message: str
    duration: Optional[str] = Field(None, description="Duration of the completed session (only on stop)")


class ActiveTimer(BaseModel):
    project: str
    started_at: str
    running_for: str = Field(..., description="How long the timer has been running, e.g. '1h 23m'")


class ActiveTimersOutput(BaseModel):
    timers: list[ActiveTimer]
    total: int
    total_completed_sessions: int = Field(0, description="Number of completed sessions across all projects (for context)")


class TimeEntry(BaseModel):
    id: int
    project: str
    started_at: str
    stopped_at: str | None = None
    duration: str | None = Field(None, description="Duration if stopped, e.g. '1h 23m'")
    status: str = Field(..., description="'running' or 'completed'")


class ListTimeEntriesInput(BaseModel):
    project: str | None = Field(None, description="Filter by project name")
    limit: int = Field(20, ge=1, le=100, description="Maximum entries to return")


class ListTimeEntriesOutput(BaseModel):
    entries: list[TimeEntry]
    total: int


class TimeSummaryInput(BaseModel):
    start_date: Optional[str] = Field(None, description="Start date in YYYY-MM-DD format. Defaults to start of current week (Monday).")
    end_date: Optional[str] = Field(None, description="End date in YYYY-MM-DD format. Defaults to today.")


class ProjectTime(BaseModel):
    project: str
    total_minutes: int
    formatted: str = Field(..., description="Human-readable duration, e.g. '2h 15m'")


class TimeSummaryOutput(BaseModel):
    start_date: str
    end_date: str
    projects: list[ProjectTime]
    total_minutes: int
    total_formatted: str
