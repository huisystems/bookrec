from datetime import date
from pathlib import Path

import pytest

from src.knowledge.store import ObsidianStore
from src.models.book import Book


class TestObsidianStore:
    @pytest.fixture
    def store(self, tmp_path):
        return ObsidianStore(str(tmp_path))

    @pytest.fixture
    def sample_book(self):
        return Book(
            title="测试图书",
            author="张三",
            publisher="科技出版社",
            published_date=date(2026, 4, 1),
            rating=8.5,
            rating_count=200,
            category="科技",
            douban_id="douban-001",
            douban_url="https://book.douban.com/subject/123456/",
            description="这是一本测试用的图书",
        )

    def test_save_and_load_new_book(self, store, sample_book):
        result = store.save_book(sample_book)
        assert result is True
        found = store.find_by_douban_id("douban-001")
        assert found is not None
        assert found.exists()
        loaded = store.load_book("douban-001")
        assert loaded is not None
        assert loaded["title"] == "测试图书"
        assert loaded["author"] == "张三"
        assert loaded["publisher"] == "科技出版社"
        assert loaded["rating"] == 8.5
        assert loaded["category"] == "科技"

    def test_save_updates_existing_file(self, store, sample_book):
        result1 = store.save_book(sample_book)
        assert result1 is True
        result2 = store.save_book(sample_book)
        assert result2 is False

    def test_dedup_same_douban_id(self, store):
        book_a = Book(
            title="原书名",
            author="张三",
            publisher="出版社",
            published_date=date(2026, 4, 1),
            rating=8.0,
            rating_count=100,
            category="科技",
            douban_id="dedup-001",
        )
        book_b = Book(
            title="新书名",
            author="张三",
            publisher="出版社",
            published_date=date(2026, 4, 1),
            rating=9.0,
            rating_count=200,
            category="科技",
            douban_id="dedup-001",
        )
        store.save_book(book_a)
        store.save_book(book_b)
        md_files = [f for f in store.root.glob("图书/**/*.md") if f.name != "__索引.md"]
        assert len(md_files) == 1
        loaded = store.load_book("dedup-001")
        assert loaded["title"] == "新书名"
        assert loaded["rating"] == 9.0

    def test_save_book_no_douban_id(self, store):
        book_a = Book(
            title="图书A",
            author="张三",
            publisher="出版社",
            published_date=date(2026, 4, 1),
            rating=8.0,
            rating_count=100,
            category="科技",
            douban_id=None,
        )
        book_b = Book(
            title="图书B",
            author="李四",
            publisher="出版社",
            published_date=date(2026, 5, 1),
            rating=7.5,
            rating_count=50,
            category="文学",
            douban_id=None,
        )
        store.save_book(book_a)
        store.save_book(book_b)
        md_files = [f for f in store.root.glob("图书/**/*.md") if f.name != "__索引.md"]
        assert len(md_files) == 2

    def test_find_by_douban_id(self, store):
        book = Book(
            title="查找测试",
            author="作者",
            publisher="出版社",
            published_date=date(2026, 4, 1),
            rating=8.0,
            rating_count=100,
            category="社科",
            douban_id="find-001",
        )
        store.save_book(book)
        path = store.find_by_douban_id("find-001")
        assert path is not None
        assert isinstance(path, Path)
        assert path.name == "查找测试.md"
        assert store.find_by_douban_id("nonexistent") is None

    def test_get_existing_ids(self, store):
        books = [
            Book("书A", "作者", "出版社", date(2026, 4, 1), 8.0, 100, "科技", douban_id="id-a"),
            Book("书B", "作者", "出版社", date(2026, 4, 1), 8.0, 100, "文学", douban_id="id-b"),
            Book("书C", "作者", "出版社", date(2026, 4, 1), 8.0, 100, "社科", douban_id="id-c"),
        ]
        for b in books:
            store.save_book(b)
        ids = store.get_existing_ids()
        assert ids == {"id-a", "id-b", "id-c"}

    def test_list_books_empty(self, store):
        assert store.list_books() == []

    def test_list_books_category_filter(self, store):
        store.save_book(
            Book("科技书", "作者", "出版社", date(2026, 4, 1), 8.0, 100, "科技", douban_id="t-001")
        )
        store.save_book(
            Book("文学书", "作者", "出版社", date(2026, 4, 1), 8.0, 100, "文学", douban_id="t-002")
        )
        store.save_book(
            Book(
                "另一科技书",
                "作者",
                "出版社",
                date(2026, 4, 1),
                9.0,
                200,
                "科技",
                douban_id="t-003",
            )
        )
        assert len(store.list_books()) == 3
        assert len(store.list_books(category="科技")) == 2
        assert len(store.list_books(category="文学")) == 1

    def test_list_books_min_rating_filter(self, store):
        store.save_book(
            Book("高分书", "作者", "出版社", date(2026, 4, 1), 9.0, 100, "科技", douban_id="r-001")
        )
        store.save_book(
            Book("中分书", "作者", "出版社", date(2026, 4, 1), 7.5, 100, "科技", douban_id="r-002")
        )
        store.save_book(
            Book("低分书", "作者", "出版社", date(2026, 4, 1), 6.0, 100, "科技", douban_id="r-003")
        )
        assert len(store.list_books(min_rating=8.0)) == 1
        assert store.list_books(min_rating=8.0)[0]["title"] == "高分书"
        assert len(store.list_books(min_rating=7.0)) == 2

    def test_add_note(self, store, sample_book):
        store.save_book(sample_book)
        store.add_note("douban-001", "这是一条测试笔记")
        filepath = store.find_by_douban_id("douban-001")
        content = filepath.read_text(encoding="utf-8")
        assert "## 笔记" in content
        assert "这是一条测试笔记" in content

    def test_add_note_overwrites(self, store, sample_book):
        store.save_book(sample_book, notes="原始笔记")
        store.add_note("douban-001", "更新后的笔记")
        filepath = store.find_by_douban_id("douban-001")
        content = filepath.read_text(encoding="utf-8")
        assert "更新后的笔记" in content
        assert "原始笔记" not in content

    def test_add_note_nonexistent_book(self, store):
        with pytest.raises(ValueError, match="未找到"):
            store.add_note("ghost-id", "这条笔记不应该被写入")

    def test_save_recommendation(self, store, sample_book):
        store.save_book(sample_book)
        title = "2026-05-TOP10"
        books_data = [{"douban_id": "douban-001"}]
        content = "# 2026年5月推荐\n\n推荐内容\n"
        store.save_recommendation(title, books_data, content)
        rec_path = store.root / "推荐列表" / f"{title}.md"
        assert rec_path.exists()
        saved = rec_path.read_text(encoding="utf-8")
        assert "2026年5月推荐" in saved

    def test_generate_index(self, store, sample_book):
        store.save_book(sample_book)
        store.save_book(
            Book(
                title="另一本书",
                author="李四",
                publisher="文学出版社",
                published_date=date(2026, 3, 1),
                rating=7.5,
                rating_count=50,
                category="文学",
                douban_id="douban-002",
            )
        )
        result = store.generate_index()
        index_path = store.root / "图书" / "__索引.md"
        assert index_path.exists()
        content = index_path.read_text(encoding="utf-8")
        assert "# 图书索引" in content
        assert "共计 2 本书" in content
        assert "测试图书" in content
        assert "另一本书" in content
        assert "## 科技" in content
        assert "## 文学" in content
        assert "测试图书" in result

    def test_update_stats(self, store, sample_book):
        store.save_book(sample_book)
        store.save_book(
            Book(
                title="文学书",
                author="李四",
                publisher="文学出版社",
                published_date=date(2026, 3, 1),
                rating=7.0,
                rating_count=50,
                category="文学",
                douban_id="douban-002",
            )
        )
        stats = store.update_stats()
        stats_path = store.root / "统计.md"
        assert stats_path.exists()
        content = stats_path.read_text(encoding="utf-8")
        assert "# 知识库统计" in content
        assert "图书总数: 2" in content
        assert stats["total"] == 2
        assert stats["by_category"]["科技"] == 1
        assert stats["by_category"]["文学"] == 1
