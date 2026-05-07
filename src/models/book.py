from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class Book:
    title: str
    author: str
    publisher: str
    published_date: date
    rating: float
    rating_count: int
    category: str
    cover_url: Optional[str] = None
    douban_url: Optional[str] = None
    description: Optional[str] = None
    catalog: Optional[str] = None
    score: Optional[float] = None

    @property
    def rating_display(self) -> str:
        return f"{self.rating:.1f}"

    @property
    def published_display(self) -> str:
        return self.published_date.strftime("%Y-%m")
