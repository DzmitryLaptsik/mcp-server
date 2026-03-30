import json
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import httpx
import msal

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

SCOPES = ["Calendars.ReadWrite"]


class OutlookCalendarProvider:
    def __init__(self):
        self.graph_url = settings.MS_GRAPH_URL
        self.cache_path = settings.MS_TOKEN_CACHE_PATH
        self.app = self._build_msal_app()
        self.token = self._authenticate()

    def _build_msal_app(self) -> msal.PublicClientApplication:
        cache = msal.SerializableTokenCache()
        if os.path.exists(self.cache_path):
            with open(self.cache_path, "r") as f:
                cache.deserialize(f.read())

        app = msal.PublicClientApplication(
            settings.MS_CLIENT_ID,
            authority=f"https://login.microsoftonline.com/{settings.MS_TENANT_ID}",
            token_cache=cache,
        )
        return app

    def _save_cache(self):
        if self.app.token_cache.has_state_changed:
            with open(self.cache_path, "w") as f:
                f.write(self.app.token_cache.serialize())

    def _authenticate(self) -> str:
        accounts = self.app.get_accounts()
        if accounts:
            result = self.app.acquire_token_silent(SCOPES, account=accounts[0])
            if result and "access_token" in result:
                self._save_cache()
                return result["access_token"]

        # Interactive device code flow (works without browser on server)
        flow = self.app.initiate_device_flow(scopes=SCOPES)
        if "user_code" not in flow:
            raise ValueError(f"Failed to initiate device flow: {flow.get('error_description', 'Unknown error')}")

        print(f"\nTo sign in to Microsoft, visit: {flow['verification_uri']}")
        print(f"Enter code: {flow['user_code']}\n")

        result = self.app.acquire_token_by_device_flow(flow)
        if "access_token" not in result:
            raise ValueError(f"Authentication failed: {result.get('error_description', 'Unknown error')}")

        self._save_cache()
        return result["access_token"]

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    async def create_event(self, input: CreateEventInput) -> EventResponse:
        event_body = {
            "subject": input.title,
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
            event_body["body"] = {"contentType": "text", "content": input.description}

        if input.attendees:
            event_body["attendees"] = [
                {"emailAddress": {"address": email}, "type": "required"}
                for email in input.attendees
            ]

        if input.recurrence:
            event_body["recurrence"] = self._parse_recurrence(input.recurrence, input.start_time)

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{self.graph_url}/me/events",
                headers=self._headers(),
                json=event_body,
            )
            response.raise_for_status()
            event = response.json()

        return EventResponse(
            id=event["id"],
            title=event.get("subject", ""),
            start_time=event["start"]["dateTime"],
            end_time=event["end"]["dateTime"],
            description=event.get("bodyPreview"),
            attendees=[a["emailAddress"]["address"] for a in event.get("attendees", [])],
            timezone=input.timezone,
            link=event.get("webLink"),
        )

    async def list_events(self, input: ListEventsInput) -> ListEventsOutput:
        start = f"{input.start_date}T00:00:00"
        end = f"{input.end_date}T23:59:59"

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{self.graph_url}/me/calendarView",
                headers=self._headers(),
                params={
                    "startDateTime": start,
                    "endDateTime": end,
                    "$orderby": "start/dateTime",
                    "$top": 50,
                    "Prefer": f'outlook.timezone="{input.timezone}"',
                },
            )
            response.raise_for_status()
            data = response.json()

        events = []
        for event in data.get("value", []):
            events.append(EventResponse(
                id=event["id"],
                title=event.get("subject", "No title"),
                start_time=event["start"]["dateTime"],
                end_time=event["end"]["dateTime"],
                description=event.get("bodyPreview"),
                attendees=[a["emailAddress"]["address"] for a in event.get("attendees", [])],
                timezone=input.timezone,
                link=event.get("webLink"),
            ))

        return ListEventsOutput(events=events, total=len(events))

    async def find_free_slots(self, input: FreeSlotsInput) -> FreeSlotsOutput:
        tz = ZoneInfo(input.timezone)
        start_dt = datetime.strptime(input.start_date, "%Y-%m-%d").replace(tzinfo=tz)
        end_dt = datetime.strptime(input.end_date, "%Y-%m-%d").replace(tzinfo=tz)

        body = {
            "schedules": input.attendees,
            "startTime": {
                "dateTime": f"{input.start_date}T00:00:00",
                "timeZone": input.timezone,
            },
            "endTime": {
                "dateTime": f"{input.end_date}T23:59:59",
                "timeZone": input.timezone,
            },
            "availabilityViewInterval": input.duration_minutes,
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{self.graph_url}/me/calendar/getSchedule",
                headers=self._headers(),
                json=body,
            )
            response.raise_for_status()
            data = response.json()

        # Collect all busy periods
        all_busy = []
        for schedule in data.get("value", []):
            for item in schedule.get("scheduleItems", []):
                busy_start = datetime.fromisoformat(item["start"]["dateTime"]).replace(tzinfo=tz)
                busy_end = datetime.fromisoformat(item["end"]["dateTime"]).replace(tzinfo=tz)
                all_busy.append((busy_start, busy_end))

        all_busy.sort(key=lambda x: x[0])

        # Merge overlapping
        merged_busy = []
        for start, end in all_busy:
            if merged_busy and start <= merged_busy[-1][1]:
                merged_busy[-1] = (merged_busy[-1][0], max(merged_busy[-1][1], end))
            else:
                merged_busy.append((start, end))

        # Find free slots (9am-6pm, weekdays)
        duration = timedelta(minutes=input.duration_minutes)
        slots = []
        current_date = start_dt

        while current_date <= end_dt:
            if current_date.weekday() >= 5:
                current_date += timedelta(days=1)
                continue

            day_start = current_date.replace(hour=9, minute=0, second=0)
            day_end = current_date.replace(hour=18, minute=0, second=0)

            cursor = day_start
            for busy_start, busy_end in merged_busy:
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

    def _parse_recurrence(self, rrule: str, start_time: str) -> dict:
        """Convert RRULE string to Microsoft Graph recurrence format."""
        start_date = start_time.split("T")[0]
        parts = {}
        for part in rrule.replace("RRULE:", "").split(";"):
            key, value = part.split("=")
            parts[key] = value

        day_map = {"MO": "monday", "TU": "tuesday", "WE": "wednesday", "TH": "thursday", "FR": "friday", "SA": "saturday", "SU": "sunday"}

        pattern = {"type": "weekly", "interval": 1}
        if "BYDAY" in parts:
            pattern["daysOfWeek"] = [day_map[d] for d in parts["BYDAY"].split(",") if d in day_map]

        recurrence_range = {"type": "noEnd", "startDate": start_date}
        if "COUNT" in parts:
            recurrence_range = {"type": "numbered", "startDate": start_date, "numberOfOccurrences": int(parts["COUNT"])}
        elif "UNTIL" in parts:
            recurrence_range = {"type": "endDate", "startDate": start_date, "endDate": parts["UNTIL"][:10]}

        return {"pattern": pattern, "range": recurrence_range}
