import importlib
import pkgutil

from mcp.server.fastmcp import FastMCP
from utils.dotenv_config import settings

mcp = FastMCP(
    "Personal Productivity Server",
    instructions=(
        "Personal productivity assistant with tools for weather, notes, tasks, "
        "time tracking, reminders, news, calendar, and timezone management. "
        "Use weather/forecast tools for location-based weather data. "
        "Use notes and tasks tools for personal data management (data persists between sessions). "
        "Use reminders to schedule time-based alerts. "
        "Use track_time/get_time_summary for project time tracking. "
        "Use calendar tools for scheduling (requires Google or Outlook setup). "
        "Use summarize_day for a combined daily briefing. "
        "Use plan_meeting to find meeting slots across timezones."
    ),
    dependencies=["httpx"],
    host=settings.MCP_HOST,
    port=settings.MCP_PORT,
)

# Auto-register all tool modules in this package.
# Any .py file or sub-package under tools/ that uses @mcp.tool() will be discovered.
for module_info in pkgutil.iter_modules(__path__):
    importlib.import_module(f".{module_info.name}", __package__)
