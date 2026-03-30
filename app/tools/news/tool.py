from mcp.server.fastmcp import Context
from mcp.types import ToolAnnotations

from tools import mcp
from tools.news.schemas import NewsInput, NewsOutput
from tools.news.service import NewsService

_news_service = None


def _get_news_service() -> NewsService:
    global _news_service
    if _news_service is None:
        _news_service = NewsService()
    return _news_service


@mcp.tool(
    description="Get latest news articles on a topic. Returns headlines, descriptions, sources, and links. Provide a topic keyword and optional max_results (1-20).",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
)
async def get_news(input: NewsInput, ctx: Context) -> NewsOutput:
    await ctx.info(f"Searching news for '{input.topic}'...")
    return await _get_news_service().get_news(input)
