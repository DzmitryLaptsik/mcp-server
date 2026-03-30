from datetime import datetime, timezone as tz
from zoneinfo import ZoneInfo

from tools.assistant.schemas import (
    DaySummaryEvents,
    DaySummaryNews,
    DaySummaryTasks,
    DaySummaryWeather,
    PlanMeetingInput,
    PlanMeetingOutput,
    SlotOption,
    SummarizeDayInput,
    SummarizeDayOutput,
)
from tools.tasks.schemas import ListTasksInput, TaskStatus
from tools.tasks.service import TasksService
from utils.dotenv_config import settings


class AssistantService:
    def __init__(self):
        self._tasks_service = TasksService()

    async def summarize_day(self, input: SummarizeDayInput) -> SummarizeDayOutput:
        today = input.date or datetime.now(ZoneInfo(input.timezone)).strftime("%Y-%m-%d")

        # 1. Calendar events (only if provider configured)
        events_summary = None
        if settings.CALENDAR_PROVIDER:
            events_summary = await self._get_events_summary(today, input.timezone)

        # 2. Tasks due today + overdue
        tasks_summary = await self._get_tasks_summary(today)

        # 3. Weather (only if city provided and API key set)
        weather_summary = None
        if input.city and settings.OPENWEATHER_API_KEY:
            weather_summary = await self._get_weather_summary(input.city, input.country)

        # 4. News (only if topic provided and API key set)
        news_summary = None
        if input.news_topic and settings.NEWSAPI_KEY:
            news_summary = await self._get_news_summary(input.news_topic)

        # Build briefing text
        briefing = self._build_briefing(today, events_summary, tasks_summary, weather_summary, news_summary)

        return SummarizeDayOutput(
            date=today,
            events=events_summary,
            tasks=tasks_summary,
            weather=weather_summary,
            news=news_summary,
            briefing=briefing,
        )

    async def plan_meeting(self, input: PlanMeetingInput) -> PlanMeetingOutput:
        if not settings.CALENDAR_PROVIDER:
            return PlanMeetingOutput(
                available_slots=[],
                total_slots=0,
                message="No calendar provider configured. Set CALENDAR_PROVIDER in .env to use this tool.",
            )

        # 1. Find free slots via calendar provider
        from tools.calendar.schemas import FreeSlotsInput
        from tools.calendar.tool import _get_calendar_provider

        provider = _get_calendar_provider()
        free_result = await provider.find_free_slots(FreeSlotsInput(
            attendees=input.attendees,
            start_date=input.start_date,
            end_date=input.end_date,
            duration_minutes=input.duration_minutes,
            timezone=input.timezone,
        ))

        # 2. Convert slot times to additional timezones if requested
        slot_options = []
        for slot in free_result.slots:
            times_in_zones = None
            if input.additional_timezones:
                times_in_zones = self._convert_slot_to_zones(
                    slot.start, input.timezone, input.additional_timezones
                )

            slot_options.append(SlotOption(
                start=slot.start,
                end=slot.end,
                times_in_zones=times_in_zones,
            ))

        # 3. Auto-book first slot if title provided
        booked_id = None
        if input.title and slot_options:
            from tools.calendar.schemas import CreateEventInput
            first = slot_options[0]

            # Calculate end time based on duration
            start_dt = datetime.fromisoformat(first.start)
            from datetime import timedelta
            end_dt = start_dt + timedelta(minutes=input.duration_minutes)

            event = await provider.create_event(CreateEventInput(
                title=input.title,
                start_time=start_dt.isoformat(),
                end_time=end_dt.isoformat(),
                attendees=input.attendees,
                timezone=input.timezone,
            ))
            booked_id = event.id

        # Build message
        if not slot_options:
            message = f"No available slots found for {input.duration_minutes}min between {input.start_date} and {input.end_date}."
        elif booked_id:
            first = slot_options[0]
            message = f"Booked '{input.title}' at {first.start} ({input.duration_minutes}min)."
            if first.times_in_zones:
                tz_parts = [f"{zone}: {time}" for zone, time in first.times_in_zones.items()]
                message += " " + ", ".join(tz_parts) + "."
        else:
            message = f"Found {len(slot_options)} available slot(s). Provide a title to auto-book the first one."

        return PlanMeetingOutput(
            available_slots=slot_options,
            total_slots=len(slot_options),
            booked_event_id=booked_id,
            message=message,
        )

    # --- Private helpers ---

    async def _get_events_summary(self, date: str, timezone: str) -> DaySummaryEvents:
        from tools.calendar.schemas import ListEventsInput
        from tools.calendar.tool import _get_calendar_provider

        provider = _get_calendar_provider()
        result = await provider.list_events(ListEventsInput(
            start_date=date,
            end_date=date,
            timezone=timezone,
        ))

        first_event = None
        first_time = None
        if result.events:
            first_event = result.events[0].title
            first_time = result.events[0].start_time

        return DaySummaryEvents(
            total=result.total,
            first_event=first_event,
            first_event_time=first_time,
        )

    async def _get_tasks_summary(self, date: str) -> DaySummaryTasks:
        # Due today: all pending/in_progress tasks (we can't filter by exact due_date easily, so get all pending)
        all_tasks = await self._tasks_service.list_tasks(ListTasksInput(status=TaskStatus.PENDING))
        due_today = sum(1 for t in all_tasks.tasks if t.due_date == date)

        overdue = await self._tasks_service.list_tasks(ListTasksInput(overdue=True))

        return DaySummaryTasks(due_today=due_today, overdue=overdue.total)

    async def _get_weather_summary(self, city: str, country: str | None) -> DaySummaryWeather:
        from tools.weather.schemas import WeatherInput
        from tools.weather.service import WeatherService

        try:
            service = WeatherService()
            result = await service.get_weather(WeatherInput(city=city, country=country))
            return DaySummaryWeather(
                temperature=result.temperature,
                description=result.description,
                city=result.city,
            )
        except Exception:
            return DaySummaryWeather()

    async def _get_news_summary(self, topic: str) -> DaySummaryNews:
        from tools.news.schemas import NewsInput
        from tools.news.service import NewsService

        try:
            service = NewsService()
            result = await service.get_news(NewsInput(topic=topic, max_results=5))
            return DaySummaryNews(
                topic=topic,
                headlines=[a.title for a in result.articles],
            )
        except Exception:
            return DaySummaryNews(topic=topic)

    def _convert_slot_to_zones(self, start_iso: str, source_tz: str, target_tzs: list[str]) -> dict[str, str]:
        start_dt = datetime.fromisoformat(start_iso)
        if start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=ZoneInfo(source_tz))

        result = {}
        for tz_name in target_tzs:
            converted = start_dt.astimezone(ZoneInfo(tz_name))
            result[tz_name] = converted.strftime("%Y-%m-%d %H:%M")
        return result

    def _build_briefing(
        self,
        date: str,
        events: DaySummaryEvents | None,
        tasks: DaySummaryTasks,
        weather: DaySummaryWeather | None,
        news: DaySummaryNews | None,
    ) -> str:
        parts = [f"Summary for {date}:"]

        if events:
            if events.total == 0:
                parts.append("No calendar events today.")
            else:
                evt_text = f"{events.total} event(s) today"
                if events.first_event:
                    evt_text += f", first: {events.first_event} at {events.first_event_time}"
                parts.append(evt_text + ".")

        task_parts = []
        if tasks.due_today > 0:
            task_parts.append(f"{tasks.due_today} task(s) due today")
        if tasks.overdue > 0:
            task_parts.append(f"{tasks.overdue} overdue")
        if task_parts:
            parts.append(", ".join(task_parts) + ".")
        else:
            parts.append("No tasks due.")

        if weather and weather.temperature is not None:
            parts.append(f"Weather in {weather.city}: {weather.temperature}°C, {weather.description}.")

        if news and news.headlines:
            parts.append(f"Top {news.topic} headlines: " + "; ".join(news.headlines[:3]) + ".")

        return " ".join(parts)
