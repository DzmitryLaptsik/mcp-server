from tools import mcp
from tools.news.schemas import NewsInput
from tools.news.service import NewsService

_news_service = None


def _get_news_service() -> NewsService:
    global _news_service
    if _news_service is None:
        _news_service = NewsService()
    return _news_service


@mcp.tool(description="Get latest news articles on a topic. Returns headlines, descriptions, sources, and links. Powered by NewsAPI.")
async def get_news(input: NewsInput):
    return await _get_news_service().get_news(input)
