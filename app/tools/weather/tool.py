from mcp.server.fastmcp import Context
from mcp.types import ToolAnnotations

from tools import mcp
from tools.weather.schemas import ForecastInput, ForecastResponse, WeatherInput, WeatherResponse
from tools.weather.service import WeatherService

_weather_service = None


def _get_weather_service() -> WeatherService:
    global _weather_service
    if _weather_service is None:
        _weather_service = WeatherService()
    return _weather_service


_READ_ONLY_OPEN = ToolAnnotations(readOnlyHint=True, openWorldHint=True)


@mcp.tool(
    description="Get current weather for a location. Provide either a city name (with optional state/country) or lat/lon coordinates. Returns temperature in Celsius and weather description.",
    annotations=_READ_ONLY_OPEN,
)
async def get_weather(location: WeatherInput, ctx: Context) -> WeatherResponse:
    await ctx.info(f"Fetching weather for {location.city or f'{location.lat},{location.lon}'}...")
    return await _get_weather_service().get_weather(location)


@mcp.tool(
    description="Get a multi-day weather forecast (1-5 days) for a location. Returns daily min/max temperatures, weather description, and rain chance percentage.",
    annotations=_READ_ONLY_OPEN,
)
async def get_forecast(input: ForecastInput, ctx: Context) -> ForecastResponse:
    await ctx.info(f"Fetching {input.days}-day forecast for {input.city or f'{input.lat},{input.lon}'}...")
    return await _get_weather_service().get_forecast(input)
