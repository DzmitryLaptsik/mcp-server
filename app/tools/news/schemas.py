from typing import Optional

from pydantic import BaseModel, Field


class NewsInput(BaseModel):
    topic: str = Field(..., description="Topic or keyword to search news for, e.g. 'AI regulations', 'tech'")
    max_results: int = Field(5, ge=1, le=20, description="Maximum number of articles to return (1-20)")


class NewsArticle(BaseModel):
    title: str
    description: Optional[str] = None
    source: str
    url: str
    published_at: str


class NewsOutput(BaseModel):
    topic: str
    articles: list[NewsArticle]
    total_results: int = Field(..., description="Total number of results available from the API")
