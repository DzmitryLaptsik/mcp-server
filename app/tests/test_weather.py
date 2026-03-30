import pytest
from unittest.mock import AsyncMock
import httpx

from tools.weather.service import WeatherService
from tools.weather.schemas import WeatherInput, WeatherResponse


def _make_response(json_data, status_code=200):
    """Helper to build a mock httpx.Response with JSON payload."""
    return httpx.Response(
        status_code=status_code,
        json=json_data,
        request=httpx.Request("GET", "https://mock.example.com"),
    )


# --- Lookup by city name (exercises geocoding + weather fetch) ---

async def test_get_weather_by_city_resolves_location_and_fetches_weather(
    weather_service: WeatherService, mock_httpx_client: AsyncMock
):
    geo_response = _make_response([
        {"lat": 51.51, "lon": -0.13, "name": "London", "state": "England", "country": "GB"}
    ])
    weather_response = _make_response({
        "main": {"temp": 14.5},
        "weather": [{"main": "Clouds"}],
    })
    mock_httpx_client.get = AsyncMock(side_effect=[geo_response, weather_response])

    result = await weather_service.get_weather(WeatherInput(city="London", country="GB"))

    assert isinstance(result, WeatherResponse)
    assert result.city == "London"
    assert result.country == "GB"
    assert result.lat == 51.51
    assert result.lon == -0.13
    assert result.temperature == 14.5
    assert result.description == "Clouds"

    # Verify both API calls were made (geocoding first, then weather)
    assert mock_httpx_client.get.call_count == 2

    geo_call = mock_httpx_client.get.call_args_list[0]
    assert "geo" in geo_call.args[0]
    assert geo_call.kwargs["params"]["q"] == "London,GB"

    weather_call = mock_httpx_client.get.call_args_list[1]
    assert "weather" in weather_call.args[0]
    assert weather_call.kwargs["params"]["lat"] == 51.51
    assert weather_call.kwargs["params"]["lon"] == -0.13


async def test_get_weather_by_city_state_country_builds_correct_query(
    weather_service: WeatherService, mock_httpx_client: AsyncMock
):
    geo_response = _make_response([
        {"lat": 40.71, "lon": -74.01, "name": "New York", "state": "New York", "country": "US"}
    ])
    weather_response = _make_response({
        "main": {"temp": 22.0},
        "weather": [{"main": "Clear"}],
    })
    mock_httpx_client.get = AsyncMock(side_effect=[geo_response, weather_response])

    result = await weather_service.get_weather(
        WeatherInput(city="New York", state="New York", country="US")
    )

    assert result.city == "New York"
    assert result.state == "New York"
    assert result.temperature == 22.0

    geo_call = mock_httpx_client.get.call_args_list[0]
    assert geo_call.kwargs["params"]["q"] == "New York,New York,US"


# --- Lookup by lat/lon (skips geocoding, single API call) ---

async def test_get_weather_by_lat_lon_skips_geocoding(
    weather_service: WeatherService, mock_httpx_client: AsyncMock
):
    weather_response = _make_response({
        "main": {"temp": 30.0},
        "weather": [{"main": "Sunny"}],
    })
    mock_httpx_client.get = AsyncMock(return_value=weather_response)

    result = await weather_service.get_weather(WeatherInput(lat=40.71, lon=-74.01))

    assert result.lat == 40.71
    assert result.lon == -74.01
    assert result.temperature == 30.0
    assert result.city == "Unknown"
    # Only one call (weather), no geocoding call
    assert mock_httpx_client.get.call_count == 1


# --- Error handling ---

async def test_get_weather_no_input_raises_value_error(weather_service: WeatherService):
    with pytest.raises(ValueError, match="You must provide either lat/lon or city name."):
        await weather_service.get_weather(WeatherInput())


async def test_get_weather_city_not_found_raises_value_error(
    weather_service: WeatherService, mock_httpx_client: AsyncMock
):
    geo_response = _make_response([])  # empty result — city not found
    mock_httpx_client.get = AsyncMock(return_value=geo_response)

    with pytest.raises(ValueError, match="City 'NonexistentCity' not found."):
        await weather_service.get_weather(WeatherInput(city="NonexistentCity"))


def test_weather_service_raises_without_api_key(monkeypatch):
    monkeypatch.setattr("tools.weather.service.settings.OPENWEATHER_API_KEY", "")
    with pytest.raises(ValueError, match="OPENWEATHER_API_KEY environment variable not set."):
        WeatherService()
