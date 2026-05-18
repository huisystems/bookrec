import pytest
from datetime import date
from src.models.book import Book
from src.output.markdown_gen import MarkdownGenerator


class TestMarkdownGenerator:

    @pytest.fixture
    def generator(self):
        return MarkdownGenerator()

    @pytest.fixture
    def sample_books(self):
        return [
            Book(
                title="Python编程",
                author="张三",
                publisher="科技出版社",
                published_date=date(2026, 4, 1),
                rating=9.0,
                rating_count=500,
                category="科技",
                tags=["Python", "编程"],
                score=85.0,
                douban_url="https://book.douban.com/subject/001/",
                description="一本Python入门书",
            ),
            Book(
                title="小说集",
                author="李四",
                publisher="文学出版社",
                published_date=date(2026, 3, 1),
                rating=7.5,
                rating_count=200,
                category="文学",
            ),
        ]

    def test_half_star_rating_9(self, generator):
        book = Book("测试", "作者", "出版社", date(2026, 4, 1), 9.0, 100, "科技")
        output = generator._format_book(book, 1)
        assert "⭐⭐⭐⭐½" in output
        assert "**豆瓣评分：** 9.0 ⭐⭐⭐⭐½ (100 人评价)" in output

    def test_half_star_rating_8(self, generator):
        book = Book("测试", "作者", "出版社", date(2026, 4, 1), 8.0, 100, "科技")
        output = generator._format_book(book, 1)
        assert "⭐⭐⭐⭐" in output
        assert "**豆瓣评分：** 8.0 ⭐⭐⭐⭐ (100 人评价)" in output

    def test_half_star_rating_7_5(self, generator):
        book = Book("测试", "作者", "出版社", date(2026, 4, 1), 7.5, 100, "科技")
        output = generator._format_book(book, 1)
        assert "⭐⭐⭐½" in output

    def test_half_star_rating_0(self, generator):
        book = Book("测试", "作者", "出版社", date(2026, 4, 1), 0.0, 100, "科技")
        output = generator._format_book(book, 1)
        assert "⭐" not in output
        assert "½" not in output

    def test_generate_output(self, generator, sample_books):
        output = generator.generate(sample_books)
        assert "# " in output
        assert "## 1. 《Python编程》" in output
        assert "## 2. 《小说集》" in output
        assert "**作者：** 张三" in output
        assert "**作者：** 李四" in output
        assert "**出版社：** 科技出版社" in output
        assert "**出版日期：** 2026-04" in output
        assert "**豆瓣评分：** 9.0 ⭐⭐⭐⭐½ (500 人评价)" in output
        assert "**豆瓣评分：** 7.5 ⭐⭐⭐½ (200 人评价)" in output
        assert "**分类：** 科技" in output
        assert "**分类：** 文学" in output
        assert "**推荐指数：** 85.0/100" in output
        assert "**标签：** Python / 编程" in output
        assert "**豆瓣链接：**" in output
        assert "book.douban.com" in output
        assert "<details>" in output
        assert "一本Python入门书" in output
        assert "---" in output
