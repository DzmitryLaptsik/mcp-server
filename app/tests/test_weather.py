import pytest
from services.weather_service import WeatherService
from schemas.weather import WeatherInput, WeatherResponse


@pytest.mark.asyncio
async def test_get_weather_by_lat_lon(weather_service: WeatherService):
    input_data = WeatherInput(lat=40.71, lon=-74.01)

    result = await weather_service.get_weather(input_data)

    assert isinstance(result, WeatherResponse)
    assert result.lat == 40.71
    assert result.lon == -74.01
    assert result.city == "Unknown"


@pytest.mark.asyncio
async def test_get_weather_no_input(weather_service: WeatherService):
    input_data = WeatherInput()
    with pytest.raises(ValueError, match="You must provide either lat/lon or city name."):
        await weather_service.get_weather(input_data)
