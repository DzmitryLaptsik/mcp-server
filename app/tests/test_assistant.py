import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from tools.assistant.schemas import (
    PlanMeetingInput,
    PlanMeetingOutput,
    SummarizeDayInput,
    SummarizeDayOutput,
)
from tools.assistant.service import AssistantService
from tools.tasks.schemas import ListTasksOutput, TaskResponse


@pytest.fixture
def assistant_service(tmp_path, monkeypatch):
    """Assistant service with tasks DB pointed to temp dir."""
    db_path = str(tmp_path / "test_tasks.db")
    monkeypatch.setattr("tools.tasks.service.settings.TASKS_DB_PATH", db_path)
    # Disable calendar, weather, news by default
    monkeypatch.setattr("tools.assistant.service.settings.CALENDAR_PROVIDER", "")
    monkeypatch.setattr("tools.assistant.service.settings.OPENWEATHER_API_KEY", "")
    monkeypatch.setattr("tools.assistant.service.settings.NEWSAPI_KEY", "")
    return AssistantService()


# --- summarize_day ---

async def test_summarize_day_tasks_only(assistant_service: AssistantService):
    """With no calendar/weather/news configured, should still return tasks summary."""
    result = await assistant_service.summarize_day(SummarizeDayInput(date="2026-03-30"))

    assert isinstance(result, SummarizeDayOutput)
    assert result.date == "2026-03-30"
    assert result.tasks.due_today == 0
    assert result.tasks.overdue == 0
    assert result.events is None
    assert result.weather is None
    assert result.news is None
    assert "Summary for 2026-03-30" in result.briefing


async def test_summarize_day_with_due_tasks(assistant_service: AssistantService):
    """Should count tasks due on the given date."""
    from tools.tasks.schemas import CreateTaskInput, TaskPriority
    await assistant_service._tasks_service.create_task(
        CreateTaskInput(title="Task A", due_date="2026-03-30")
    )
    await assistant_service._tasks_service.create_task(
        CreateTaskInput(title="Task B", due_date="2026-03-30")
    )
    await assistant_service._tasks_service.create_task(
        CreateTaskInput(title="Task C", due_date="2026-04-01")
    )

    result = await assistant_service.summarize_day(SummarizeDayInput(date="2026-03-30"))

    assert result.tasks.due_today == 2
    assert "2 task(s) due today" in result.briefing


async def test_summarize_day_with_overdue_tasks(assistant_service: AssistantService):
    from tools.tasks.schemas import CreateTaskInput
    await assistant_service._tasks_service.create_task(
        CreateTaskInput(title="Overdue task", due_date="2020-01-01")
    )

    result = await assistant_service.summarize_day(SummarizeDayInput(date="2026-03-30"))

    assert result.tasks.overdue == 1
    assert "1 overdue" in result.briefing


async def test_summarize_day_with_weather(assistant_service: AssistantService, monkeypatch):
    monkeypatch.setattr("tools.assistant.service.settings.OPENWEATHER_API_KEY", "mock_key")

    mock_weather_response = MagicMock()
    mock_weather_response.temperature = 22.0
    mock_weather_response.description = "Sunny"
    mock_weather_response.city = "London"

    mock_service_instance = MagicMock()
    mock_service_instance.get_weather = AsyncMock(return_value=mock_weather_response)

    with patch("tools.weather.service.WeatherService", return_value=mock_service_instance):
        result = await assistant_service.summarize_day(
            SummarizeDayInput(date="2026-03-30", city="London", country="GB")
        )

    assert result.weather is not None
    assert result.weather.temperature == 22.0
    assert "22.0°C" in result.briefing


async def test_summarize_day_with_news(assistant_service: AssistantService, monkeypatch):
    monkeypatch.setattr("tools.assistant.service.settings.NEWSAPI_KEY", "mock_key")

    mock_news_response = MagicMock()
    mock_news_response.articles = [
        MagicMock(title="AI regulation advances"),
        MagicMock(title="New GPT model released"),
    ]

    mock_service_instance = MagicMock()
    mock_service_instance.get_news = AsyncMock(return_value=mock_news_response)

    with patch("tools.news.service.NewsService", return_value=mock_service_instance):
        result = await assistant_service.summarize_day(
            SummarizeDayInput(date="2026-03-30", news_topic="AI")
        )

    assert result.news is not None
    assert len(result.news.headlines) == 2
    assert "AI regulation advances" in result.briefing


# --- plan_meeting ---

async def test_plan_meeting_no_provider(assistant_service: AssistantService):
    """With no calendar provider, should return helpful message."""
    result = await assistant_service.plan_meeting(PlanMeetingInput(
        attendees=["a@example.com"],
        start_date="2026-04-01",
        end_date="2026-04-03",
    ))

    assert isinstance(result, PlanMeetingOutput)
    assert result.total_slots == 0
    assert "No calendar provider configured" in result.message


async def test_plan_meeting_with_slots(assistant_service: AssistantService, monkeypatch):
    monkeypatch.setattr("tools.assistant.service.settings.CALENDAR_PROVIDER", "google")

    from tools.calendar.schemas import FreeSlot, FreeSlotsOutput

    mock_free_result = FreeSlotsOutput(
        slots=[
            FreeSlot(start="2026-04-01T09:00:00+00:00", end="2026-04-01T10:00:00+00:00"),
            FreeSlot(start="2026-04-01T14:00:00+00:00", end="2026-04-01T16:00:00+00:00"),
        ],
        total=2,
    )

    mock_provider = AsyncMock()
    mock_provider.find_free_slots = AsyncMock(return_value=mock_free_result)

    with patch("tools.calendar.tool._get_calendar_provider", return_value=mock_provider):
        result = await assistant_service.plan_meeting(PlanMeetingInput(
            attendees=["alex@example.com"],
            start_date="2026-04-01",
            end_date="2026-04-03",
            duration_minutes=60,
        ))

    assert result.total_slots == 2
    assert result.booked_event_id is None
    assert "2 available slot(s)" in result.message


async def test_plan_meeting_with_timezone_conversion(assistant_service: AssistantService, monkeypatch):
    monkeypatch.setattr("tools.assistant.service.settings.CALENDAR_PROVIDER", "google")

    from tools.calendar.schemas import FreeSlot, FreeSlotsOutput

    mock_free_result = FreeSlotsOutput(
        slots=[FreeSlot(start="2026-04-01T09:00:00+00:00", end="2026-04-01T18:00:00+00:00")],
        total=1,
    )

    mock_provider = AsyncMock()
    mock_provider.find_free_slots = AsyncMock(return_value=mock_free_result)

    with patch("tools.calendar.tool._get_calendar_provider", return_value=mock_provider):
        result = await assistant_service.plan_meeting(PlanMeetingInput(
            attendees=["user@example.com"],
            start_date="2026-04-01",
            end_date="2026-04-01",
            timezone="UTC",
            additional_timezones=["Asia/Tokyo", "Europe/London"],
        ))

    assert result.total_slots == 1
    slot = result.available_slots[0]
    assert slot.times_in_zones is not None
    assert "Asia/Tokyo" in slot.times_in_zones
    assert "Europe/London" in slot.times_in_zones


async def test_plan_meeting_auto_book(assistant_service: AssistantService, monkeypatch):
    monkeypatch.setattr("tools.assistant.service.settings.CALENDAR_PROVIDER", "google")

    from tools.calendar.schemas import FreeSlot, FreeSlotsOutput

    mock_free_result = FreeSlotsOutput(
        slots=[FreeSlot(start="2026-04-01T10:00:00+00:00", end="2026-04-01T12:00:00+00:00")],
        total=1,
    )

    mock_event = MagicMock()
    mock_event.id = "evt_booked_123"

    mock_provider = AsyncMock()
    mock_provider.find_free_slots = AsyncMock(return_value=mock_free_result)
    mock_provider.create_event = AsyncMock(return_value=mock_event)

    with patch("tools.calendar.tool._get_calendar_provider", return_value=mock_provider):
        result = await assistant_service.plan_meeting(PlanMeetingInput(
            attendees=["alex@example.com", "maria@example.com"],
            start_date="2026-04-01",
            end_date="2026-04-03",
            duration_minutes=60,
            title="Team Sync",
        ))

    assert result.booked_event_id == "evt_booked_123"
    assert "Booked 'Team Sync'" in result.message
    mock_provider.create_event.assert_called_once()
