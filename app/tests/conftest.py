import pytest
from unittest.mock import AsyncMock
from pytest_mock import MockerFixture
from tools.weather.service import WeatherService


@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    """Patches the settings attributes where WeatherService actually reads them."""
    monkeypatch.setattr("tools.weather.service.settings.OPENWEATHER_API_KEY", "mock_api_key")
    monkeypatch.setattr("tools.weather.service.settings.STATIC_GEO_URL", "https://mock-geo.example.com/geo")
    monkeypatch.setattr("tools.weather.service.settings.STATIC_WEATHER_URL", "https://mock-weather.example.com/weather")
    monkeypatch.setattr("tools.weather.service.settings.STATIC_FORECAST_URL", "https://mock-forecast.example.com/forecast")


@pytest.fixture
def weather_service():
    """Provides a fresh instance of WeatherService for each test."""
    return WeatherService()


@pytest.fixture
def mock_httpx_client(mocker: MockerFixture):
    """Mocks httpx.AsyncClient as an async context manager returning an AsyncMock client."""
    mock_client = AsyncMock()
    mock_context = AsyncMock()
    mock_context.__aenter__ = AsyncMock(return_value=mock_client)
    mock_context.__aexit__ = AsyncMock(return_value=False)
    mocker.patch("httpx.AsyncClient", return_value=mock_context)
    return mock_client
