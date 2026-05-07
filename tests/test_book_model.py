import pytest
from datetime import date
from src.models.book import Book


class TestBookModel:
    def test_rating_display(self):
        book = Book(
            title="测试",
            author="作者",
            publisher="出版社",
            published_date=date(2026, 4, 1),
            rating=8.567,
            rating_count=100,
            category="文学",
        )
        assert book.rating_display == "8.6"

    def test_rating_display_integer(self):
        book = Book(
            title="测试",
            author="作者",
            publisher="出版社",
            published_date=date(2026, 4, 1),
            rating=9.0,
            rating_count=100,
            category="文学",
        )
        assert book.rating_display == "9.0"

    def test_published_display(self):
        book = Book(
            title="测试",
            author="作者",
            publisher="出版社",
            published_date=date(2026, 4, 15),
            rating=8.0,
            rating_count=100,
            category="文学",
        )
        assert book.published_display == "2026-04"

    def test_book_creation(self):
        book = Book(
            title="书名",
            author="作者",
            publisher="出版社",
            published_date=date(2026, 4, 1),
            rating=8.5,
            rating_count=200,
            category="科技",
            description="简介",
            catalog="目录",
        )
        assert book.title == "书名"
        assert book.description == "简介"
        assert book.catalog == "目录"

    def test_optional_fields_default(self):
        book = Book(
            title="测试",
            author="作者",
            publisher="出版社",
            published_date=date(2026, 4, 1),
            rating=8.0,
            rating_count=100,
            category="文学",
        )
        assert book.cover_url is None
        assert book.douban_url is None
        assert book.description is None
        assert book.catalog is None
        assert book.score is None