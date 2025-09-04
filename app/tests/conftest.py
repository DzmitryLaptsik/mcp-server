import pytest
from httpx import AsyncClient
from pytest_mock import MockerFixture
from services.weather_service import WeatherService


@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    """Mocks the environment variables for API keys."""
    monkeypatch.setenv("OPENWEATHER_API_KEY", "mock_api_key")


@pytest.fixture
def mock_httpx_client(mocker: MockerFixture):
    """Mocks the httpx.AsyncClient for external API calls."""
    mock_client = mocker.MagicMock(spec=AsyncClient)
    mocker.patch('httpx.AsyncClient', return_value=mock_client)
    return mock_client


@pytest.fixture
def weather_service(mock_env_vars):
    """Provides a fresh instance of WeatherService for each test."""
    return WeatherService()
