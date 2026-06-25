from datetime import date
from typing import List, Optional

from dateutil.relativedelta import relativedelta

from ..models.book import Book


class BookFilter:
    """书籍筛选器"""

    def __init__(
        self,
        max_months: int = 12,
        min_rating: float = 7.0,
        min_rating_count: int = 20,
        exclude_keywords: Optional[List[str]] = None,
    ):
        self.max_months = max_months
        self.min_rating = min_rating
        self.min_rating_count = min_rating_count
        self.exclude_keywords = exclude_keywords or [
            "考试", "教材", "教辅", "习题", "真题"
        ]

    def filter(self, books: List[Book], months: Optional[int] = None) -> List[Book]:
        months = months or self.max_months
        # 使用 relativedelta 做精确月份回退（避免 30 天估算导致的边界漂移）
        cutoff_date = date.today().replace(day=1) - relativedelta(months=months)

        filtered = []
        for book in books:
            if book.published_date < cutoff_date:
                continue
            if book.rating < self.min_rating:
                continue
            if book.rating_count < self.min_rating_count:
                continue
            if self._is_excluded(book):
                continue
            filtered.append(book)

        return filtered

    def _is_excluded(self, book: Book) -> bool:
        text = book.title + book.category + book.author
        return any(kw in text for kw in self.exclude_keywords)


class BookRanker:
    """书籍排序器"""

    def __init__(
        self,
        rating_weight: float = 0.4,
        recency_weight: float = 0.3,
        popularity_weight: float = 0.3,
    ):
        self.rating_weight = rating_weight
        self.recency_weight = recency_weight
        self.popularity_weight = popularity_weight

    def rank(self, books: List[Book]) -> List[Book]:
        max_rating_count = max((b.rating_count for b in books), default=1)
        today = date.today()
        max_days = 365

        for book in books:
            rating_score = book.rating / 10.0
            days_since_pub = (today - book.published_date).days
            recency_score = max(0, 1 - (days_since_pub / max_days))
            popularity_score = min(1.0, book.rating_count / max(max_rating_count, 1))

            book.score = (
                rating_score * self.rating_weight
                + recency_score * self.recency_weight
                + popularity_score * self.popularity_weight
            ) * 100

        return sorted(books, key=lambda b: b.score or 0, reverse=True)
