import pytest
from unittest.mock import AsyncMock
import httpx

from tools.news.schemas import NewsInput, NewsOutput
from tools.news.service import NewsService


@pytest.fixture(autouse=True)
def mock_news_env(monkeypatch):
    monkeypatch.setattr("tools.news.service.settings.NEWSAPI_KEY", "mock_news_key")
    monkeypatch.setattr("tools.news.service.settings.NEWSAPI_URL", "https://mock-news.example.com/news")


@pytest.fixture
def news_service():
    return NewsService()


@pytest.fixture
def mock_httpx_news(mocker):
    mock_client = AsyncMock()
    mock_context = AsyncMock()
    mock_context.__aenter__ = AsyncMock(return_value=mock_client)
    mock_context.__aexit__ = AsyncMock(return_value=False)
    mocker.patch("httpx.AsyncClient", return_value=mock_context)
    return mock_client


def _make_response(json_data, status_code=200):
    return httpx.Response(
        status_code=status_code,
        json=json_data,
        request=httpx.Request("GET", "https://mock-news.example.com"),
    )


async def test_get_news(news_service: NewsService, mock_httpx_news: AsyncMock):
    api_response = _make_response({
        "totalResults": 100,
        "articles": [
            {
                "title": "AI Regulation Update",
                "description": "New AI laws proposed in EU",
                "source": {"name": "TechNews"},
                "url": "https://example.com/article1",
                "publishedAt": "2026-03-30T10:00:00Z",
            },
            {
                "title": "GPT-5 Released",
                "description": None,
                "source": {"name": "AIDaily"},
                "url": "https://example.com/article2",
                "publishedAt": "2026-03-30T08:00:00Z",
            },
        ],
    })
    mock_httpx_news.get = AsyncMock(return_value=api_response)

    result = await news_service.get_news(NewsInput(topic="AI", max_results=5))

    assert isinstance(result, NewsOutput)
    assert result.topic == "AI"
    assert result.total_results == 100
    assert len(result.articles) == 2
    assert result.articles[0].title == "AI Regulation Update"
    assert result.articles[0].source == "TechNews"
    assert result.articles[1].description is None

    call_kwargs = mock_httpx_news.get.call_args.kwargs
    assert call_kwargs["params"]["q"] == "AI"
    assert call_kwargs["params"]["pageSize"] == 5
    assert call_kwargs["params"]["apiKey"] == "mock_news_key"


async def test_get_news_empty_results(news_service: NewsService, mock_httpx_news: AsyncMock):
    api_response = _make_response({"totalResults": 0, "articles": []})
    mock_httpx_news.get = AsyncMock(return_value=api_response)

    result = await news_service.get_news(NewsInput(topic="obscure topic"))
    assert result.total_results == 0
    assert result.articles == []


def test_news_service_raises_without_api_key(monkeypatch):
    monkeypatch.setattr("tools.news.service.settings.NEWSAPI_KEY", "")
    with pytest.raises(ValueError, match="NEWSAPI_KEY environment variable not set."):
        NewsService()
