from schemas.weather import WeatherInput
from services.weather_service import WeatherService

weather_service = WeatherService()


async def get_weather_tool(location: WeatherInput):
    return await weather_service.get_weather(location)
