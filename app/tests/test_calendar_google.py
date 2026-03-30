import pytest
from unittest.mock import MagicMock, patch

from tools.calendar.schemas import (
    CreateEventInput,
    EventResponse,
    FreeSlotsOutput,
    FreeSlotsInput,
    ListEventsInput,
    ListEventsOutput,
)
from tools.calendar.google_calendar import GoogleCalendarProvider


@pytest.fixture
def google_provider(monkeypatch):
    """Create a GoogleCalendarProvider with mocked auth and API service."""
    monkeypatch.setattr("tools.calendar.google_calendar.settings.GOOGLE_CLIENT_ID", "mock_id")
    monkeypatch.setattr("tools.calendar.google_calendar.settings.GOOGLE_CLIENT_SECRET", "mock_secret")
    monkeypatch.setattr("tools.calendar.google_calendar.settings.GOOGLE_TOKEN_PATH", "/tmp/nonexistent_token.json")

    mock_creds = MagicMock()
    mock_creds.valid = True
    mock_creds.expired = False

    mock_service = MagicMock()

    with patch.object(GoogleCalendarProvider, "_authenticate", return_value=mock_creds), \
         patch("tools.calendar.google_calendar.build", return_value=mock_service):
        provider = GoogleCalendarProvider()

    provider.service = mock_service
    return provider


async def test_create_event(google_provider: GoogleCalendarProvider):
    mock_event = {
        "id": "evt_123",
        "summary": "Team Standup",
        "start": {"dateTime": "2026-03-31T09:00:00"},
        "end": {"dateTime": "2026-03-31T09:15:00"},
        "attendees": [{"email": "alex@example.com"}],
        "htmlLink": "https://calendar.google.com/event/evt_123",
    }
    google_provider.service.events.return_value.insert.return_value.execute.return_value = mock_event

    result = await google_provider.create_event(CreateEventInput(
        title="Team Standup",
        start_time="2026-03-31T09:00:00",
        end_time="2026-03-31T09:15:00",
        attendees=["alex@example.com"],
        timezone="America/New_York",
    ))

    assert isinstance(result, EventResponse)
    assert result.id == "evt_123"
    assert result.title == "Team Standup"
    assert result.attendees == ["alex@example.com"]
    assert result.link == "https://calendar.google.com/event/evt_123"


async def test_create_event_with_recurrence(google_provider: GoogleCalendarProvider):
    mock_event = {
        "id": "evt_rec",
        "summary": "Daily Standup",
        "start": {"dateTime": "2026-03-31T09:00:00"},
        "end": {"dateTime": "2026-03-31T09:15:00"},
        "htmlLink": "https://calendar.google.com/event/evt_rec",
    }
    google_provider.service.events.return_value.insert.return_value.execute.return_value = mock_event

    result = await google_provider.create_event(CreateEventInput(
        title="Daily Standup",
        start_time="2026-03-31T09:00:00",
        end_time="2026-03-31T09:15:00",
        recurrence="RRULE:FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR",
    ))

    # Verify recurrence was included in the API call
    call_kwargs = google_provider.service.events.return_value.insert.call_args.kwargs
    assert "recurrence" in call_kwargs["body"]
    assert result.id == "evt_rec"


async def test_list_events(google_provider: GoogleCalendarProvider):
    mock_result = {
        "items": [
            {
                "id": "evt_1",
                "summary": "Meeting",
                "start": {"dateTime": "2026-03-31T10:00:00"},
                "end": {"dateTime": "2026-03-31T11:00:00"},
            },
            {
                "id": "evt_2",
                "summary": "Lunch",
                "start": {"dateTime": "2026-03-31T12:00:00"},
                "end": {"dateTime": "2026-03-31T13:00:00"},
            },
        ]
    }
    google_provider.service.events.return_value.list.return_value.execute.return_value = mock_result

    result = await google_provider.list_events(ListEventsInput(
        start_date="2026-03-31",
        end_date="2026-04-04",
        timezone="UTC",
    ))

    assert isinstance(result, ListEventsOutput)
    assert result.total == 2
    assert result.events[0].title == "Meeting"
    assert result.events[1].title == "Lunch"


async def test_find_free_slots(google_provider: GoogleCalendarProvider):
    mock_freebusy = {
        "calendars": {
            "alex@example.com": {
                "busy": [
                    {"start": "2026-04-01T10:00:00+00:00", "end": "2026-04-01T11:00:00+00:00"},
                    {"start": "2026-04-01T14:00:00+00:00", "end": "2026-04-01T15:00:00+00:00"},
                ]
            }
        }
    }
    google_provider.service.freebusy.return_value.query.return_value.execute.return_value = mock_freebusy

    result = await google_provider.find_free_slots(FreeSlotsInput(
        attendees=["alex@example.com"],
        start_date="2026-04-01",
        end_date="2026-04-01",
        duration_minutes=60,
        timezone="UTC",
    ))

    assert isinstance(result, FreeSlotsOutput)
    assert result.total >= 1  # Should find slots: 9-10, 11-14, 15-18
