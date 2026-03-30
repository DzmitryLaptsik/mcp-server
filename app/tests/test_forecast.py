import pytest
from unittest.mock import AsyncMock
import httpx

from tools.weather.service import WeatherService
from tools.weather.schemas import ForecastInput, ForecastResponse


def _make_response(json_data, status_code=200):
    return httpx.Response(
        status_code=status_code,
        json=json_data,
        request=httpx.Request("GET", "https://mock.example.com"),
    )


async def test_get_forecast_by_city(weather_service: WeatherService, mock_httpx_client: AsyncMock):
    geo_response = _make_response([
        {"lat": 51.51, "lon": -0.13, "name": "London", "state": "England", "country": "GB"}
    ])
    forecast_response = _make_response({
        "list": [
            {"dt_txt": "2026-03-30 09:00:00", "main": {"temp": 10.0}, "weather": [{"main": "Clouds"}], "pop": 0.2},
            {"dt_txt": "2026-03-30 12:00:00", "main": {"temp": 14.0}, "weather": [{"main": "Clouds"}], "pop": 0.1},
            {"dt_txt": "2026-03-30 15:00:00", "main": {"temp": 13.0}, "weather": [{"main": "Rain"}], "pop": 0.8},
            {"dt_txt": "2026-03-31 09:00:00", "main": {"temp": 8.0}, "weather": [{"main": "Clear"}], "pop": 0.0},
            {"dt_txt": "2026-03-31 12:00:00", "main": {"temp": 12.0}, "weather": [{"main": "Clear"}], "pop": 0.0},
        ]
    })
    mock_httpx_client.get = AsyncMock(side_effect=[geo_response, forecast_response])

    result = await weather_service.get_forecast(ForecastInput(city="London", country="GB", days=2))

    assert isinstance(result, ForecastResponse)
    assert result.city == "London"
    assert result.country == "GB"
    assert len(result.days) == 2

    day1 = result.days[0]
    assert day1.date == "2026-03-30"
    assert day1.temp_min == 10.0
    assert day1.temp_max == 14.0
    assert day1.description == "Clouds"
    assert day1.rain_chance == 33  # 1 of 3 entries has pop > 0.3

    day2 = result.days[1]
    assert day2.date == "2026-03-31"
    assert day2.temp_min == 8.0
    assert day2.temp_max == 12.0
    assert day2.description == "Clear"
    assert day2.rain_chance == 0


async def test_get_forecast_by_lat_lon(weather_service: WeatherService, mock_httpx_client: AsyncMock):
    forecast_response = _make_response({
        "list": [
            {"dt_txt": "2026-04-01 12:00:00", "main": {"temp": 25.0}, "weather": [{"main": "Sunny"}], "pop": 0.0},
        ]
    })
    mock_httpx_client.get = AsyncMock(return_value=forecast_response)

    result = await weather_service.get_forecast(ForecastInput(lat=40.71, lon=-74.01, days=1))

    assert result.city == "Unknown"
    assert len(result.days) == 1
    assert result.days[0].temp_max == 25.0
    assert mock_httpx_client.get.call_count == 1  # no geocoding


async def test_get_forecast_no_input_raises(weather_service: WeatherService):
    with pytest.raises(ValueError, match="You must provide either lat/lon or city name."):
        await weather_service.get_forecast(ForecastInput(days=3))


async def test_get_forecast_limits_days(weather_service: WeatherService, mock_httpx_client: AsyncMock):
    forecast_response = _make_response({
        "list": [
            {"dt_txt": f"2026-04-0{i} 12:00:00", "main": {"temp": 20.0}, "weather": [{"main": "Clear"}], "pop": 0.0}
            for i in range(1, 6)
        ]
    })
    mock_httpx_client.get = AsyncMock(return_value=forecast_response)

    result = await weather_service.get_forecast(ForecastInput(lat=0, lon=0, days=2))
    assert len(result.days) == 2
