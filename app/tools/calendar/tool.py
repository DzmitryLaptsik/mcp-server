from mcp.types import ToolAnnotations

from tools import mcp
from tools.calendar.base import CalendarProvider
from tools.calendar.schemas import (
    CreateEventInput,
    EventResponse,
    FreeSlotsInput,
    FreeSlotsOutput,
    ListEventsInput,
    ListEventsOutput,
)
from utils.dotenv_config import settings

_calendar_provider = None


def _get_calendar_provider() -> CalendarProvider:
    global _calendar_provider
    if _calendar_provider is None:
        provider = settings.CALENDAR_PROVIDER.lower()
        if provider == "google":
            from tools.calendar.google_calendar import GoogleCalendarProvider
            _calendar_provider = GoogleCalendarProvider()
        elif provider == "outlook":
            from tools.calendar.outlook_calendar import OutlookCalendarProvider
            _calendar_provider = OutlookCalendarProvider()
        else:
            raise ValueError(
                f"Unknown CALENDAR_PROVIDER: '{settings.CALENDAR_PROVIDER}'. "
                "Set it to 'google' or 'outlook' in your .env file."
            )
    return _calendar_provider


@mcp.tool(
    description="Create a NEW calendar event. Only use when the user explicitly asks to schedule, create, or book an event. Do NOT use when the user asks to see or list events — use list_calendar_events instead.",
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=True),
)
async def create_calendar_event(input: CreateEventInput) -> EventResponse:
    return await _get_calendar_provider().create_event(input)


@mcp.tool(
    description="List existing calendar events within a date range. Use when the user asks to show, check, or view calendar events.",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
)
async def list_calendar_events(input: ListEventsInput) -> ListEventsOutput:
    return await _get_calendar_provider().list_events(input)


@mcp.tool(
    description="Find available time slots for a meeting with given attendees within a date range. Checks all attendees' calendars for conflicts (9am-6pm weekdays).",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
)
async def find_free_slots(input: FreeSlotsInput) -> FreeSlotsOutput:
    return await _get_calendar_provider().find_free_slots(input)
