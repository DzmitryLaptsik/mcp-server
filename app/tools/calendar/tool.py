from tools import mcp
from tools.calendar.base import CalendarProvider
from tools.calendar.schemas import CreateEventInput, FreeSlotsInput, ListEventsInput
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


@mcp.tool(description="Create a calendar event with title, time, optional attendees, and recurrence. Supports Google Calendar and Outlook.")
async def create_calendar_event(input: CreateEventInput):
    return await _get_calendar_provider().create_event(input)


@mcp.tool(description="List calendar events within a date range. Returns all events sorted by start time.")
async def list_calendar_events(input: ListEventsInput):
    return await _get_calendar_provider().list_events(input)


@mcp.tool(description="Find available time slots for a meeting with given attendees within a date range. Checks all attendees' calendars for conflicts.")
async def find_free_slots(input: FreeSlotsInput):
    return await _get_calendar_provider().find_free_slots(input)
