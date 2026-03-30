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
