"""Orchestrator.search / Orchestrator.add_note 的直接集成测试

补 test_orchestrator.py 没覆盖的两个用户调用面：
  - search: 全文搜索 (title / author / description)
  - add_note: 添加 / 覆盖个人笔记

依赖真实文件系统 (tmp_path) + MagicMock 替换网络源，不依赖豆瓣。
"""

from datetime import date
from unittest.mock import MagicMock

import pytest

from src.models.book import Book
from src.services.orchestrator import Orchestrator


@pytest.fixture
def orch(tmp_path):
    o = Orchestrator(vault_path=str(tmp_path), timeout=1000)
    o.source = MagicMock()
    return o


def _book(*, douban_id, title="测试书", author="作者", category="AI", description=""):
    return Book(
        title=title,
        author=author,
        publisher="出版社",
        published_date=date(2026, 4, 1),
        rating=8.0,
        rating_count=100,
        category=category,
        douban_url=f"https://book.douban.com/subject/{douban_id}/",
        douban_id=douban_id,
        description=description,
    )


# ─── search ────────────────────────────────────────


class TestSearch:
    def test_search_finds_by_title(self, orch):
        """search 能按书名命中（命中 frontmatter title 字段）"""
        orch.store.save_book(_book(douban_id="s1", title="深度学习入门"))
        orch.store.save_book(_book(douban_id="s2", title="Python编程"))

        results = orch.search("深度学习")

        assert len(results) == 1
        assert results[0]["title"] == "深度学习入门"

    def test_search_finds_by_author_in_body(self, orch):
        """search 全文匹配，能命中 markdown body（不仅是 frontmatter）"""
        orch.store.save_book(_book(douban_id="a1", title="某书", author="斋藤康毅"))
        orch.store.save_book(_book(douban_id="a2", title="另一书", author="其他人"))

        results = orch.search("斋藤康毅")

        assert len(results) == 1
        assert results[0]["douban_id"] == "a1"

    def test_search_is_case_insensitive(self, orch):
        """search 大小写不敏感（实现: query.lower() in content.lower()）"""
        orch.store.save_book(_book(douban_id="c1", title="Transformers in Action"))

        # 库里是大写 T, 查询用小写 t
        results = orch.search("transformers")
        assert len(results) == 1

    def test_search_no_match_returns_empty_list(self, orch):
        """search 无命中时返回空 list，不抛异常"""
        orch.store.save_book(_book(douban_id="n1", title="A"))
        orch.store.save_book(_book(douban_id="n2", title="B"))

        results = orch.search("绝对不存在于任何书里的关键词xyz123")

        assert results == []

    def test_search_skips_index_file(self, orch):
        """search 不应把 __索引.md 当成图书命中（实现里有显式 skip）"""
        orch.store.save_book(_book(douban_id="k1", title="目标"))
        orch.store.generate_index()

        # 搜索一个能在索引里出现、但也真的出现在书里的词
        # 索引里也会包含 "目标" 这种 — 因此 search 必须仍能命中书
        # 但更重要的是: 索引文件本身不能被当成"额外的书"返回
        results = orch.search("目标")
        for r in results:
            assert r.get("douban_id") == "k1"


# ─── add_note ──────────────────────────────────────


class TestAddNote:
    def test_add_note_creates_section_when_absent(self, orch):
        """首次添加笔记时, 应在文件末尾追加 ## 笔记 节"""
        orch.store.save_book(_book(douban_id="n1", title="书"))

        orch.add_note("n1", "我的第一条笔记")

        content = (orch.store.root / "图书" / "AI" / "书.md").read_text(encoding="utf-8")
        assert "## 笔记" in content
        assert "我的第一条笔记" in content

    def test_add_note_overwrites_existing(self, orch):
        """重复 add_note 应覆盖原笔记, 不应追加成多份"""
        orch.store.save_book(_book(douban_id="n2", title="书"))

        orch.add_note("n2", "第一条笔记")
        orch.add_note("n2", "第二条笔记，覆盖前一条")

        content = (orch.store.root / "图书" / "AI" / "书.md").read_text(encoding="utf-8")
        assert content.count("## 笔记") == 1
        assert "第一条笔记" not in content
        assert "第二条笔记，覆盖前一条" in content

    def test_add_note_nonexistent_raises_value_error(self, orch):
        """add_note 一个不存在的 douban_id 应抛 ValueError"""
        with pytest.raises(ValueError, match="未找到 douban_id"):
            orch.add_note("ghost-id", "无处安放的笔记")
