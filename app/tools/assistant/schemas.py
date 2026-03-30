from typing import Optional

from pydantic import BaseModel, Field


# --- summarize_day ---

class SummarizeDayInput(BaseModel):
    date: Optional[str] = Field(None, description="Date to summarize in YYYY-MM-DD format. Defaults to today.")
    city: Optional[str] = Field(None, description="City for weather info. Optional.")
    country: Optional[str] = Field(None, description="Country ISO code for weather. Optional.")
    news_topic: Optional[str] = Field(None, description="Topic for news headlines. Optional.")
    timezone: str = Field("UTC", description="IANA timezone for the summary")


class DaySummaryEvents(BaseModel):
    total: int
    first_event: Optional[str] = None
    first_event_time: Optional[str] = None


class DaySummaryTasks(BaseModel):
    due_today: int
    overdue: int


class DaySummaryWeather(BaseModel):
    temperature: Optional[float] = None
    description: Optional[str] = None
    city: Optional[str] = None


class DaySummaryNews(BaseModel):
    topic: Optional[str] = None
    headlines: list[str] = Field(default_factory=list)


class SummarizeDayOutput(BaseModel):
    date: str
    events: Optional[DaySummaryEvents] = None
    tasks: DaySummaryTasks
    weather: Optional[DaySummaryWeather] = None
    news: Optional[DaySummaryNews] = None
    briefing: str = Field(..., description="Human-readable summary of the day")


# --- plan_meeting ---

class PlanMeetingInput(BaseModel):
    attendees: list[str] = Field(..., description="List of attendee email addresses")
    duration_minutes: int = Field(60, description="Meeting duration in minutes")
    start_date: str = Field(..., description="Start of date range to search in YYYY-MM-DD format")
    end_date: str = Field(..., description="End of date range to search in YYYY-MM-DD format")
    timezone: str = Field("UTC", description="Primary timezone for displaying results")
    additional_timezones: Optional[list[str]] = Field(None, description="Additional IANA timezones to show slot times in, e.g. ['Asia/Tokyo', 'Europe/London']")
    title: Optional[str] = Field(None, description="If provided, automatically book the first available slot with this title")


class SlotOption(BaseModel):
    start: str
    end: str
    times_in_zones: Optional[dict[str, str]] = Field(None, description="Start time in each requested timezone")


class PlanMeetingOutput(BaseModel):
    available_slots: list[SlotOption]
    total_slots: int
    booked_event_id: Optional[str] = Field(None, description="Event ID if auto-booked")
    message: str
