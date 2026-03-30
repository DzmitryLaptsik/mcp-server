from typing import Optional

from pydantic import BaseModel, Field


class CreateEventInput(BaseModel):
    title: str = Field(..., description="Event title/summary")
    start_time: str = Field(..., description="Start time in ISO format: YYYY-MM-DDTHH:MM:SS")
    end_time: str = Field(..., description="End time in ISO format: YYYY-MM-DDTHH:MM:SS")
    description: Optional[str] = Field(None, description="Event description or notes")
    attendees: Optional[list[str]] = Field(None, description="List of attendee email addresses")
    timezone: str = Field("UTC", description="IANA timezone for the event, e.g. 'America/New_York'")
    recurrence: Optional[str] = Field(None, description="Recurrence rule, e.g. 'RRULE:FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR'")


class EventResponse(BaseModel):
    id: str = Field(..., description="Event ID from the calendar provider")
    title: str
    start_time: str
    end_time: str
    description: Optional[str] = None
    attendees: list[str] = Field(default_factory=list)
    timezone: str = "UTC"
    link: Optional[str] = Field(None, description="Link to the event in the calendar provider")


class ListEventsInput(BaseModel):
    start_date: str = Field(..., description="Start of date range in YYYY-MM-DD format")
    end_date: str = Field(..., description="End of date range in YYYY-MM-DD format")
    timezone: str = Field("UTC", description="IANA timezone for interpreting dates")


class ListEventsOutput(BaseModel):
    events: list[EventResponse]
    total: int


class FreeSlotsInput(BaseModel):
    attendees: list[str] = Field(..., description="List of attendee email addresses to check availability for")
    start_date: str = Field(..., description="Start of date range in YYYY-MM-DD format")
    end_date: str = Field(..., description="End of date range in YYYY-MM-DD format")
    duration_minutes: int = Field(60, description="Required meeting duration in minutes")
    timezone: str = Field("UTC", description="IANA timezone for the results")


class FreeSlot(BaseModel):
    start: str = Field(..., description="Slot start time in ISO format")
    end: str = Field(..., description="Slot end time in ISO format")


class FreeSlotsOutput(BaseModel):
    slots: list[FreeSlot]
    total: int
