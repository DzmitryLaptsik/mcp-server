import httpx

from tools.news.schemas import NewsArticle, NewsInput, NewsOutput
from utils.dotenv_config import settings


class NewsService:
    def __init__(self):
        self.api_key = settings.NEWSAPI_KEY
        self.api_url = settings.NEWSAPI_URL
        if not self.api_key:
            raise ValueError("NEWSAPI_KEY environment variable not set.")

    async def get_news(self, input: NewsInput) -> NewsOutput:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                self.api_url,
                params={
                    "q": input.topic,
                    "pageSize": input.max_results,
                    "sortBy": "publishedAt",
                    "apiKey": self.api_key,
                },
            )
            response.raise_for_status()
            data = response.json()

        articles = [
            NewsArticle(
                title=article["title"] or "Untitled",
                description=article.get("description"),
                source=article["source"]["name"],
                url=article["url"],
                published_at=article["publishedAt"],
            )
            for article in data.get("articles", [])
        ]

        return NewsOutput(
            topic=input.topic,
            articles=articles,
            total_results=data.get("totalResults", 0),
        )
