from datetime import date, timedelta
from typing import List

from ..models.book import Book


class BookFilter:
    """书籍筛选器"""

    def __init__(
        self,
        max_months: int = 6,
        min_rating: float = 7.5,
        min_rating_count: int = 100,
        exclude_keywords: List[str] = None
    ):
        self.max_months = max_months
        self.min_rating = min_rating
        self.min_rating_count = min_rating_count
        self.exclude_keywords = exclude_keywords or ["考试", "教材", "教辅", "习题", "真题"]

    def filter(self, books: List[Book], months: int = None) -> List[Book]:
        """筛选书籍"""
        months = months or self.max_months
        cutoff_date = date.today().replace(day=1) - timedelta(days=30 * months)

        filtered = []
        for book in books:
            # 1. 日期过滤
            if book.published_date < cutoff_date:
                continue

            # 2. 评分过滤
            if book.rating < self.min_rating:
                continue

            # 3. 评价人数过滤（防刷分）
            if book.rating_count < self.min_rating_count:
                continue

            # 4. 排除类别过滤
            if self._is_excluded(book):
                continue

            filtered.append(book)

        return filtered

    def _is_excluded(self, book: Book) -> bool:
        """检查是否应该排除"""
        text = book.title + book.category + book.author
        return any(kw in text for kw in self.exclude_keywords)


class BookRanker:
    """书籍排序器"""

    def __init__(self, rating_weight: float = 0.4, recency_weight: float = 0.3, popularity_weight: float = 0.3):
        self.rating_weight = rating_weight
        self.recency_weight = recency_weight
        self.popularity_weight = popularity_weight

    def rank(self, books: List[Book]) -> List[Book]:
        """综合评分排序"""
        max_rating_count = max((b.rating_count for b in books), default=1)
        today = date.today()
        max_days = 180  # 最多半年的数据

        for book in books:
            # 评分归一化 (0-10 -> 0-1)
            rating_score = book.rating / 10.0

            # 新鲜度分数 (越新越高)
            days_since_pub = (today - book.published_date).days
            recency_score = max(0, 1 - (days_since_pub / max_days))

            # 热度分数 (评价人数归一化)
            popularity_score = min(1.0, book.rating_count / max(max_rating_count, 1))

            # 综合得分
            book.score = (
                rating_score * self.rating_weight +
                recency_score * self.recency_weight +
                popularity_score * self.popularity_weight
            ) * 100  # 转为百分制

        return sorted(books, key=lambda b: b.score, reverse=True)
