from tools import mcp
from tools.assistant.schemas import PlanMeetingInput, SummarizeDayInput
from tools.assistant.service import AssistantService

_assistant_service = None


def _get_assistant_service() -> AssistantService:
    global _assistant_service
    if _assistant_service is None:
        _assistant_service = AssistantService()
    return _assistant_service


@mcp.tool(description="Get a daily briefing: calendar events, tasks due, weather, and news headlines. Chains multiple tools into one summary. Configure which parts to include via optional fields.")
async def summarize_day(input: SummarizeDayInput):
    return await _get_assistant_service().summarize_day(input)


@mcp.tool(description="Plan a meeting across timezones. Finds available slots for all attendees, shows times in multiple timezones, and optionally auto-books the first slot. Chains calendar + timezone tools.")
async def plan_meeting(input: PlanMeetingInput):
    return await _get_assistant_service().plan_meeting(input)
