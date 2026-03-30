import asyncio
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from tools.calendar.schemas import (
    CreateEventInput,
    EventResponse,
    FreeSlot,
    FreeSlotsInput,
    FreeSlotsOutput,
    ListEventsInput,
    ListEventsOutput,
)
from utils.dotenv_config import settings

SCOPES = ["https://www.googleapis.com/auth/calendar"]


class GoogleCalendarProvider:
    def __init__(self):
        self.token_path = settings.GOOGLE_TOKEN_PATH
        self.creds = self._authenticate()
        self.service = build("calendar", "v3", credentials=self.creds)

    def _authenticate(self) -> Credentials:
        creds = None

        if os.path.exists(self.token_path):
            creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)

        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            self._save_token(creds)
        elif not creds or not creds.valid:
            client_config = {
                "installed": {
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": ["http://localhost"],
                }
            }
            flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
            creds = flow.run_local_server(port=0)
            self._save_token(creds)

        return creds

    def _save_token(self, creds: Credentials):
        with open(self.token_path, "w") as f:
            f.write(creds.to_json())

    async def create_event(self, input: CreateEventInput) -> EventResponse:
        event_body = {
            "summary": input.title,
            "start": {
                "dateTime": input.start_time,
                "timeZone": input.timezone,
            },
            "end": {
                "dateTime": input.end_time,
                "timeZone": input.timezone,
            },
        }

        if input.description:
            event_body["description"] = input.description

        if input.attendees:
            event_body["attendees"] = [{"email": email} for email in input.attendees]

        if input.recurrence:
            event_body["recurrence"] = [input.recurrence]

        event = await asyncio.to_thread(
            self.service.events().insert(calendarId="primary", body=event_body).execute
        )

        return EventResponse(
            id=event["id"],
            title=event.get("summary", ""),
            start_time=event["start"].get("dateTime", event["start"].get("date", "")),
            end_time=event["end"].get("dateTime", event["end"].get("date", "")),
            description=event.get("description"),
            attendees=[a["email"] for a in event.get("attendees", [])],
            timezone=input.timezone,
            link=event.get("htmlLink"),
        )

    async def list_events(self, input: ListEventsInput) -> ListEventsOutput:
        time_min = f"{input.start_date}T00:00:00"
        time_max = f"{input.end_date}T23:59:59"

        events_result = await asyncio.to_thread(
            self.service.events()
            .list(
                calendarId="primary",
                timeMin=self._to_rfc3339(time_min, input.timezone),
                timeMax=self._to_rfc3339(time_max, input.timezone),
                singleEvents=True,
                orderBy="startTime",
                timeZone=input.timezone,
            )
            .execute
        )

        events = []
        for event in events_result.get("items", []):
            events.append(EventResponse(
                id=event["id"],
                title=event.get("summary", "No title"),
                start_time=event["start"].get("dateTime", event["start"].get("date", "")),
                end_time=event["end"].get("dateTime", event["end"].get("date", "")),
                description=event.get("description"),
                attendees=[a["email"] for a in event.get("attendees", [])],
                timezone=input.timezone,
                link=event.get("htmlLink"),
            ))

        return ListEventsOutput(events=events, total=len(events))

    async def find_free_slots(self, input: FreeSlotsInput) -> FreeSlotsOutput:
        time_min = f"{input.start_date}T00:00:00"
        time_max = f"{input.end_date}T23:59:59"

        body = {
            "timeMin": self._to_rfc3339(time_min, input.timezone),
            "timeMax": self._to_rfc3339(time_max, input.timezone),
            "timeZone": input.timezone,
            "items": [{"id": email} for email in input.attendees],
        }

        freebusy = await asyncio.to_thread(
            self.service.freebusy().query(body=body).execute
        )

        # Collect all busy periods across all attendees
        all_busy = []
        for calendar_id, calendar_data in freebusy.get("calendars", {}).items():
            for busy in calendar_data.get("busy", []):
                all_busy.append((
                    datetime.fromisoformat(busy["start"]),
                    datetime.fromisoformat(busy["end"]),
                ))

        all_busy.sort(key=lambda x: x[0])

        # Merge overlapping busy periods
        merged_busy = []
        for start, end in all_busy:
            if merged_busy and start <= merged_busy[-1][1]:
                merged_busy[-1] = (merged_busy[-1][0], max(merged_busy[-1][1], end))
            else:
                merged_busy.append((start, end))

        # Find free slots between busy periods (9am-6pm working hours)
        tz = ZoneInfo(input.timezone)
        start_date = datetime.strptime(input.start_date, "%Y-%m-%d").replace(tzinfo=tz)
        end_date = datetime.strptime(input.end_date, "%Y-%m-%d").replace(tzinfo=tz)
        duration = timedelta(minutes=input.duration_minutes)

        slots = []
        current_date = start_date
        while current_date <= end_date:
            day_start = current_date.replace(hour=9, minute=0, second=0)
            day_end = current_date.replace(hour=18, minute=0, second=0)

            if current_date.weekday() >= 5:
                current_date += timedelta(days=1)
                continue

            cursor = day_start
            for busy_start, busy_end in merged_busy:
                busy_start = busy_start.astimezone(tz)
                busy_end = busy_end.astimezone(tz)

                if busy_end <= day_start or busy_start >= day_end:
                    continue

                if cursor + duration <= busy_start:
                    slots.append(FreeSlot(
                        start=cursor.isoformat(),
                        end=busy_start.isoformat(),
                    ))
                cursor = max(cursor, busy_end)

            if cursor + duration <= day_end:
                slots.append(FreeSlot(
                    start=cursor.isoformat(),
                    end=day_end.isoformat(),
                ))

            current_date += timedelta(days=1)

        return FreeSlotsOutput(slots=slots, total=len(slots))

    def _to_rfc3339(self, dt_str: str, timezone: str) -> str:
        dt = datetime.fromisoformat(dt_str).replace(tzinfo=ZoneInfo(timezone))
        return dt.isoformat()
