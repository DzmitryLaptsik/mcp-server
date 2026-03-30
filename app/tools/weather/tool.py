from tools import mcp
from tools.weather.schemas import ForecastInput, WeatherInput
from tools.weather.service import WeatherService

_weather_service = None


def _get_weather_service() -> WeatherService:
    global _weather_service
    if _weather_service is None:
        _weather_service = WeatherService()
    return _weather_service


@mcp.tool(description="Get current weather for a location. Also get the temperature in Celsius.")
async def get_weather(location: WeatherInput):
    return await _get_weather_service().get_weather(location)


@mcp.tool(description="Get a multi-day weather forecast (1-5 days) for a location. Returns daily min/max temperatures, weather description, and rain chance.")
async def get_forecast(input: ForecastInput):
    return await _get_weather_service().get_forecast(input)
