import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from tools.calendar.schemas import (
    CreateEventInput,
    EventResponse,
    FreeSlotsInput,
    FreeSlotsOutput,
    ListEventsInput,
    ListEventsOutput,
)
from tools.calendar.outlook_calendar import OutlookCalendarProvider


def _make_response(json_data, status_code=200):
    return httpx.Response(
        status_code=status_code,
        json=json_data,
        request=httpx.Request("GET", "https://graph.microsoft.com"),
    )


@pytest.fixture
def outlook_provider(monkeypatch):
    """Create an OutlookCalendarProvider with mocked auth."""
    monkeypatch.setattr("tools.calendar.outlook_calendar.settings.MS_CLIENT_ID", "mock_id")
    monkeypatch.setattr("tools.calendar.outlook_calendar.settings.MS_CLIENT_SECRET", "mock_secret")
    monkeypatch.setattr("tools.calendar.outlook_calendar.settings.MS_TENANT_ID", "common")
    monkeypatch.setattr("tools.calendar.outlook_calendar.settings.MS_TOKEN_CACHE_PATH", "/tmp/nonexistent_cache.json")
    monkeypatch.setattr("tools.calendar.outlook_calendar.settings.MS_GRAPH_URL", "https://mock-graph.example.com/v1.0")

    with patch.object(OutlookCalendarProvider, "_build_msal_app", return_value=MagicMock()), \
         patch.object(OutlookCalendarProvider, "_authenticate", return_value="mock_access_token"):
        provider = OutlookCalendarProvider()

    return provider


@pytest.fixture
def mock_httpx_outlook(mocker):
    mock_client = AsyncMock()
    mock_context = AsyncMock()
    mock_context.__aenter__ = AsyncMock(return_value=mock_client)
    mock_context.__aexit__ = AsyncMock(return_value=False)
    mocker.patch("httpx.AsyncClient", return_value=mock_context)
    return mock_client


async def test_create_event(outlook_provider: OutlookCalendarProvider, mock_httpx_outlook: AsyncMock):
    api_response = _make_response({
        "id": "AAMk_123",
        "subject": "Team Sync",
        "start": {"dateTime": "2026-03-31T09:00:00"},
        "end": {"dateTime": "2026-03-31T10:00:00"},
        "attendees": [{"emailAddress": {"address": "maria@example.com"}}],
        "webLink": "https://outlook.office.com/event/AAMk_123",
        "bodyPreview": "Weekly sync",
    })
    mock_httpx_outlook.post = AsyncMock(return_value=api_response)

    result = await outlook_provider.create_event(CreateEventInput(
        title="Team Sync",
        start_time="2026-03-31T09:00:00",
        end_time="2026-03-31T10:00:00",
        description="Weekly sync",
        attendees=["maria@example.com"],
    ))

    assert isinstance(result, EventResponse)
    assert result.id == "AAMk_123"
    assert result.title == "Team Sync"
    assert result.attendees == ["maria@example.com"]
    assert result.link == "https://outlook.office.com/event/AAMk_123"


async def test_list_events(outlook_provider: OutlookCalendarProvider, mock_httpx_outlook: AsyncMock):
    api_response = _make_response({
        "value": [
            {
                "id": "AAMk_1",
                "subject": "Morning Meeting",
                "start": {"dateTime": "2026-03-31T09:00:00"},
                "end": {"dateTime": "2026-03-31T10:00:00"},
                "attendees": [],
            },
            {
                "id": "AAMk_2",
                "subject": "Dentist",
                "start": {"dateTime": "2026-04-02T14:00:00"},
                "end": {"dateTime": "2026-04-02T15:00:00"},
                "attendees": [],
            },
        ]
    })
    mock_httpx_outlook.get = AsyncMock(return_value=api_response)

    result = await outlook_provider.list_events(ListEventsInput(
        start_date="2026-03-31",
        end_date="2026-04-04",
    ))

    assert isinstance(result, ListEventsOutput)
    assert result.total == 2
    assert result.events[0].title == "Morning Meeting"
    assert result.events[1].title == "Dentist"


async def test_find_free_slots(outlook_provider: OutlookCalendarProvider, mock_httpx_outlook: AsyncMock):
    api_response = _make_response({
        "value": [
            {
                "scheduleItems": [
                    {
                        "start": {"dateTime": "2026-04-01T10:00:00"},
                        "end": {"dateTime": "2026-04-01T11:00:00"},
                    },
                ]
            }
        ]
    })
    mock_httpx_outlook.post = AsyncMock(return_value=api_response)

    result = await outlook_provider.find_free_slots(FreeSlotsInput(
        attendees=["sarah@example.com"],
        start_date="2026-04-01",
        end_date="2026-04-01",
        duration_minutes=60,
        timezone="UTC",
    ))

    assert isinstance(result, FreeSlotsOutput)
    assert result.total >= 1


async def test_create_event_with_recurrence(outlook_provider: OutlookCalendarProvider, mock_httpx_outlook: AsyncMock):
    api_response = _make_response({
        "id": "AAMk_rec",
        "subject": "Daily Standup",
        "start": {"dateTime": "2026-03-31T09:00:00"},
        "end": {"dateTime": "2026-03-31T09:15:00"},
        "attendees": [],
    })
    mock_httpx_outlook.post = AsyncMock(return_value=api_response)

    result = await outlook_provider.create_event(CreateEventInput(
        title="Daily Standup",
        start_time="2026-03-31T09:00:00",
        end_time="2026-03-31T09:15:00",
        recurrence="RRULE:FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR",
    ))

    assert result.id == "AAMk_rec"
    # Verify recurrence was sent to the API
    call_kwargs = mock_httpx_outlook.post.call_args.kwargs
    assert "recurrence" in call_kwargs["json"]
    recurrence = call_kwargs["json"]["recurrence"]
    assert "monday" in recurrence["pattern"]["daysOfWeek"]
    assert "friday" in recurrence["pattern"]["daysOfWeek"]
