"""
MCP Prompts — user-facing reusable message templates.
Prompts are user-controlled (the user selects them from a menu in the client).
"""

from tools import mcp


@mcp.prompt()
def daily_briefing(city: str = "New York", timezone: str = "America/New_York") -> str:
    """Get a morning briefing with weather, calendar, tasks, and news."""
    return (
        f"Give me my daily briefing for today. "
        f"My city is {city} and my timezone is {timezone}. "
        f"Include calendar events, pending tasks, weather, and top news headlines."
    )


@mcp.prompt()
def schedule_meeting(
    attendees: str = "alex@example.com",
    duration: str = "60",
    date_range: str = "this week",
) -> str:
    """Find a time to meet with someone across timezones."""
    return (
        f"I need to schedule a {duration}-minute meeting with {attendees} "
        f"sometime {date_range}. "
        f"Find available slots and show me the times in all relevant timezones."
    )


@mcp.prompt()
def quick_note(content: str = "") -> str:
    """Save a quick note with automatic tagging."""
    if content:
        return f"Save this as a note and add appropriate tags: {content}"
    return "I want to save a note. Ask me what to write."


@mcp.prompt()
def task_review() -> str:
    """Review current tasks and priorities."""
    return (
        "Show me all my pending and in-progress tasks. "
        "Group them by project if possible, highlight any that are overdue, "
        "and suggest what I should focus on today."
    )


@mcp.prompt()
def time_report(period: str = "this week") -> str:
    """Get a time tracking summary."""
    return (
        f"Give me a time tracking report for {period}. "
        f"Show time per project and total hours. "
        f"If I have any active timers running, mention those too."
    )


@mcp.prompt()
def travel_check(city: str = "", date: str = "") -> str:
    """Check weather and timezone for a trip."""
    parts = ["I'm planning to travel"]
    if city:
        parts.append(f"to {city}")
    if date:
        parts.append(f"on {date}")
    parts.append(
        ". Tell me the current weather, the forecast for the next few days, "
        "what time it is there now, and the timezone difference from my location."
    )
    return " ".join(parts)
