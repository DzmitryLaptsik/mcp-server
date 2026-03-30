from typing import Protocol

from tools.calendar.schemas import (
    CreateEventInput,
    EventResponse,
    FreeSlotsInput,
    FreeSlotsOutput,
    ListEventsInput,
    ListEventsOutput,
)


class CalendarProvider(Protocol):
    async def create_event(self, input: CreateEventInput) -> EventResponse: ...
    async def list_events(self, input: ListEventsInput) -> ListEventsOutput: ...
    async def find_free_slots(self, input: FreeSlotsInput) -> FreeSlotsOutput: ...
