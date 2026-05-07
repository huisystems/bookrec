import pytest
from datetime import date
from src.models.book import Book
from src.services.filter import BookFilter, BookRanker


@pytest.fixture
def sample_books():
    return [
        Book(
            title="Python编程",
            author="张三",
            publisher="科技出版社",
            published_date=date(2026, 3, 1),
            rating=8.5,
            rating_count=500,
            category="科技",
        ),
        Book(
            title="算法导论",
            author="李四",
            publisher="计算机出版社",
            published_date=date(2026, 4, 1),
            rating=9.0,
            rating_count=300,
            category="科技",
        ),
        Book(
            title="小说集",
            author="王五",
            publisher="文学出版社",
            published_date=date(2026, 2, 1),
            rating=7.5,
            rating_count=100,
            category="文学",
        ),
        Book(
            title="考试指南",
            author="赵六",
            publisher="教育出版社",
            published_date=date(2026, 5, 1),
            rating=8.0,
            rating_count=50,
            category="其他",
        ),
    ]


class TestBookFilter:
    def test_date_filter(self):
        filter_obj = BookFilter(max_months=3, min_rating=0, min_rating_count=0)
        books = [
            Book("旧书", "作者", "出版社", date(2025, 1, 1), 8.0, 100, "文学"),
            Book("新书", "作者", "出版社", date(2026, 4, 1), 8.0, 100, "文学"),
        ]
        result = filter_obj.filter(books)
        assert len(result) == 1
        assert result[0].title == "新书"

    def test_rating_filter(self):
        filter_obj = BookFilter(max_months=12, min_rating=8.0, min_rating_count=0)
        books = [
            Book("高分书", "作者", "出版社", date(2026, 4, 1), 8.5, 100, "文学"),
            Book("低分书", "作者", "出版社", date(2026, 4, 1), 7.0, 100, "文学"),
        ]
        result = filter_obj.filter(books)
        assert len(result) == 1
        assert result[0].title == "高分书"

    def test_exclude_keywords(self):
        filter_obj = BookFilter(max_months=12, min_rating=0, min_rating_count=0)
        books = [
            Book("考试指南", "作者", "出版社", date(2026, 4, 1), 8.0, 100, "其他"),
            Book("正常书籍", "作者", "出版社", date(2026, 4, 1), 8.0, 100, "文学"),
        ]
        result = filter_obj.filter(books)
        assert len(result) == 1
        assert result[0].title == "正常书籍"

    def test_combined_filter(self, sample_books):
        filter_obj = BookFilter(max_months=3, min_rating=8.0, min_rating_count=200)
        result = filter_obj.filter(sample_books)
        assert len(result) == 2


class TestBookRanker:
    def test_ranking_scores(self):
        ranker = BookRanker(rating_weight=0.4, recency_weight=0.3, popularity_weight=0.3)
        books = [
            Book("高分新书", "作者", "出版社", date(2026, 5, 1), 9.0, 500, "科技"),
            Book("低分旧书", "作者", "出版社", date(2026, 1, 1), 7.0, 100, "科技"),
        ]
        ranked = ranker.rank(books)
        assert ranked[0].title == "高分新书"
        assert ranked[0].score is not None
        assert ranked[1].score is not None

    def test_recency_weight(self):
        ranker = BookRanker(rating_weight=0.0, recency_weight=1.0, popularity_weight=0.0)
        books = [
            Book("旧书", "作者", "出版社", date(2025, 1, 1), 5.0, 1000, "文学"),
            Book("新书", "作者", "出版社", date(2026, 5, 1), 5.0, 1000, "文学"),
        ]
        ranked = ranker.rank(books)
        assert ranked[0].title == "新书"

    def test_sorted_output(self, sample_books):
        ranker = BookRanker()
        ranked = ranker.rank(sample_books)
        for i in range(len(ranked) - 1):
            assert ranked[i].score >= ranked[i + 1].score