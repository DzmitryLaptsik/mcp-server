from mcp.types import ToolAnnotations

from tools import mcp
from tools.reminders.schemas import ListRemindersInput, ListRemindersOutput, ReminderResponse, SetReminderInput
from tools.reminders.service import RemindersService

_reminders_service = None


def _get_reminders_service() -> RemindersService:
    global _reminders_service
    if _reminders_service is None:
        _reminders_service = RemindersService()
    return _reminders_service


@mcp.tool(
    description="Create a NEW reminder. Only use when the user explicitly asks to set, create, or add a reminder. Do NOT use when the user asks to see, list, or check reminders — use list_reminders instead.",
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False),
)
async def set_reminder(input: SetReminderInput) -> ReminderResponse:
    return await _get_reminders_service().set_reminder(input)


@mcp.tool(
    description="List existing pending reminders. Use when the user asks to show, list, view, or check reminders. Optionally include already-fired reminders.",
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def list_reminders(input: ListRemindersInput) -> ListRemindersOutput:
    return await _get_reminders_service().list_reminders(include_fired=input.include_fired or False)
