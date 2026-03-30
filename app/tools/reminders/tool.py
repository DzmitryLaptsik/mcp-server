from typing import Optional

from pydantic import BaseModel, Field

from tools import mcp
from tools.reminders.schemas import SetReminderInput
from tools.reminders.service import RemindersService

_reminders_service = None


def _get_reminders_service() -> RemindersService:
    global _reminders_service
    if _reminders_service is None:
        _reminders_service = RemindersService()
    return _reminders_service


@mcp.tool(description="Set a reminder with a message. Provide either an absolute time (remind_at) or a relative offset in minutes (remind_in_minutes).")
async def set_reminder(input: SetReminderInput):
    return await _get_reminders_service().set_reminder(input)


class ListRemindersInput(BaseModel):
    include_fired: Optional[bool] = Field(False, description="If true, include already-fired reminders")


@mcp.tool(description="List pending reminders. Optionally include already-fired reminders.")
async def list_reminders(input: ListRemindersInput):
    return await _get_reminders_service().list_reminders(include_fired=input.include_fired or False)
