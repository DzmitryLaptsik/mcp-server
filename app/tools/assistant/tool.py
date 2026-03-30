from mcp.server.fastmcp import Context
from mcp.types import ToolAnnotations

from tools import mcp
from tools.assistant.schemas import PlanMeetingInput, PlanMeetingOutput, SummarizeDayInput, SummarizeDayOutput
from tools.assistant.service import AssistantService

_assistant_service = None


def _get_assistant_service() -> AssistantService:
    global _assistant_service
    if _assistant_service is None:
        _assistant_service = AssistantService()
    return _assistant_service


@mcp.tool(
    description="Get a daily briefing: calendar events, tasks due, weather, and news headlines. Chains multiple tools into one summary. Set city for weather, news_topic for headlines.",
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def summarize_day(input: SummarizeDayInput, ctx: Context) -> SummarizeDayOutput:
    await ctx.info("Building daily summary...")
    await ctx.report_progress(0, 4)
    result = await _get_assistant_service().summarize_day(input)
    await ctx.report_progress(4, 4)
    return result


@mcp.tool(
    description="Plan a meeting across timezones. Finds available slots for all attendees, shows times in multiple timezones, and optionally auto-books if title is provided.",
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=True),
)
async def plan_meeting(input: PlanMeetingInput, ctx: Context) -> PlanMeetingOutput:
    await ctx.info(f"Finding meeting slots for {len(input.attendees)} attendee(s)...")
    return await _get_assistant_service().plan_meeting(input)
