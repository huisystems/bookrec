"""Orchestrator 集成测试

不依赖网络：用 tmp_path 建真实知识库 + MagicMock 替换 DoubanBookSource。
覆盖 fetch/recommend/stats/history 主路径，以及月份窗口边界回归。
"""

import logging
from datetime import date
from unittest.mock import MagicMock

import pytest

from src.models.book import Book
from src.services.orchestrator import Orchestrator


@pytest.fixture
def vault(tmp_path):
    return str(tmp_path)


@pytest.fixture
def source():
    """Mock 的 DoubanBookSource（不发起网络）"""
    return MagicMock()


@pytest.fixture
def orch(vault, source):
    o = Orchestrator(vault_path=vault, timeout=1000)
    o.source = source
    return o


def _book(
    *,
    douban_id: str,
    title: str = None,
    author: str = "作者",
    category: str = "AI",
    rating: float = 8.0,
    rating_count: int = 100,
    published: date = None,
    description: str = "",
) -> Book:
    return Book(
        title=title or f"测试书-{douban_id}",
        author=author,
        publisher="出版社",
        published_date=published or date(2026, 4, 1),
        rating=rating,
        rating_count=rating_count,
        category=category,
        douban_url=f"https://book.douban.com/subject/{douban_id}/",
        douban_id=douban_id,
        description=description,
    )


def _stub_detail_filler(source):
    """让 mock 的 fetch_book_detail 真的给 book.description 赋值

    默认 MagicMock 的 side_effect=auto 会把返回设为 Mock 对象，book.description = Mock()
    不让 `not description` 为真，触发不了 orchestrator 的更新分支。"""
    def fill(book):
        book.description = f"已补全: {book.title}"
        return book
    source.fetch_book_detail.side_effect = fill


# ─── fetch_all 去重与入库 ─────────────────────────────


class TestFetchAll:
    def test_fetch_all_dedupes_across_categories(self, orch, source, vault):
        """同一 douban_id 在两次抓取中重复出现，应只入库一次"""
        b1 = _book(douban_id="100", title="A", category="经管")
        b2 = _book(douban_id="100", title="A", category="AI")
        source.fetch_latest.return_value = [b1]
        source.fetch_tag_books.return_value = [b2]

        result = orch.fetch_all(categories=["经管", "AI"], months=12, max_pages=1)

        assert result["new"] == 1
        assert result["duplicates"] >= 0
        # 知识库里只应有一份
        ids = orch.store.get_existing_ids()
        assert ids == {"100"}

    def test_fetch_skips_existing_with_description(self, orch, source, vault):
        """重复抓取时已有 description → 不重抓详情、不更新"""
        existing = _book(douban_id="200", description="已有简介")
        orch.store.save_book(existing)

        again = _book(douban_id="200", description="")
        source.fetch_latest.return_value = [again]
        source.fetch_tag_books.return_value = []

        result = orch.fetch_all(categories=["经管"], months=12, max_pages=1)

        assert result["new"] == 0
        assert result["updated"] == 0
        # 关键契约：description 已有就不再 fetch_book_detail
        source.fetch_book_detail.assert_not_called()
        # 库里仍只有 1 本
        assert orch.store.get_existing_ids() == {"200"}

    def test_fetch_updates_existing_without_description(self, orch, source, vault):
        """重复抓取时已有但缺 description → 触发详情抓取并更新"""
        _stub_detail_filler(source)
        existing = _book(douban_id="300", description="")
        orch.store.save_book(existing)

        again = _book(douban_id="300", description="")
        # AI 路径对 3 个 tag 各调一次 fetch_tag_books；
        # 第一次返回命中书, 后续返回空, 模拟真实抓取不会 3 个 tag 都返回同一本
        source.fetch_tag_books.side_effect = [[again], [], []]

        result = orch.fetch_all(categories=["AI"], months=12, max_pages=1)

        assert result["updated"] == 1
        # 应调用详情抓取
        source.fetch_book_detail.assert_called_once()
        # fetch_book_detail 应当填充 description
        assert again.description != ""

    def test_fetch_continues_when_detail_fails(self, orch, source, vault, caplog):
        """fetch_book_detail 抛异常时不让整批 fetch 挂掉"""
        source.fetch_book_detail.side_effect = RuntimeError("网络炸了")
        b = _book(douban_id="400")
        source.fetch_latest.return_value = [b]
        source.fetch_tag_books.return_value = []

        with caplog.at_level(logging.WARNING):
            result = orch.fetch_all(categories=["经管"], months=12, max_pages=1)

        # 即便详情失败，主体仍应入库
        assert result["new"] == 1
        assert "获取详情失败" in caplog.text


# ─── recommend 排序与持久化 ──────────────────────────


class TestRecommend:
    def test_recommend_ranking_and_save(self, orch, vault):
        """recommend 按 score 倒序、限制 top_n、写推荐文件"""
        # 直接写 5 本到知识库（绕过 fetch）
        books = [
            _book(douban_id="r1", title="高分新书", rating=9.0, rating_count=500,
                  published=date(2026, 5, 1)),
            _book(douban_id="r2", title="中等", rating=8.0, rating_count=200,
                  published=date(2026, 4, 1)),
            _book(douban_id="r3", title="低分旧书", rating=7.0, rating_count=50,
                  published=date(2025, 1, 1)),
        ]
        for b in books:
            orch.store.save_book(b)

        result = orch.recommend(top_n=2, min_rating=7.0, min_rating_count=20, months=12)

        assert result["count"] == 2
        # 排序：高 rating + 高 popularity + 近日期 优先
        assert result["books"][0].title in ("高分新书", "中等")
        # 推荐文件已写入
        rec_dir = orch.store.root / "推荐列表"
        rec_files = list(rec_dir.glob("*.md"))
        assert len(rec_files) == 1
        assert "TOP 2" in rec_files[0].read_text(encoding="utf-8")

    def test_recommend_no_candidates(self, orch, vault):
        """知识库为空或全被过滤掉时，返回空、不写文件、不抛"""
        result = orch.recommend(top_n=10, min_rating=9.9, months=12)
        assert result["books"] == []
        assert result["markdown"] == ""
        assert result["count"] == 0

        rec_files = list((orch.store.root / "推荐列表").glob("*.md"))
        assert rec_files == []


# ─── 知识库查询 / 统计 / 历史 ─────────────────────────


class TestQueryAndStats:
    def test_stats_aggregates_by_category(self, orch):
        for cat, did in [("AI", "s1"), ("AI", "s2"), ("经管", "b1")]:
            orch.store.save_book(_book(douban_id=did, category=cat))

        stats = orch.stats()
        assert stats["total"] == 3
        assert stats["by_category"].get("AI") == 2
        assert stats["by_category"].get("经管") == 1

    def test_history_lists_recommendation_files(self, orch, vault):
        orch.store.save_recommendation("2026-05-TOP", [], "# empty")
        orch.store.save_recommendation("2026-06-TOP", [], "# empty")

        names = orch.history()
        assert "2026-06-TOP.md" in names
        assert "2026-05-TOP.md" in names
        # 按时间倒序
        assert names.index("2026-06-TOP.md") < names.index("2026-05-TOP.md")


# ─── 回归：月份窗口必须用日历精确月 ─────────────────────


class TestMonthWindowRegression:
    def test_load_books_from_store_window_uses_calendar_month(self, orch):
        """months=3 时 cutoff 应是 3 个日历月前的月初，不能用 30*months 近似

        复现：今天 2026-06-26，months=3
          - 错误实现：cutoff = 2026-06-01 - 90 days = 2026-03-03
            → 2026-03-01 出版的书被错误排除
          - 正确实现：cutoff = 2026-03-01（relativedelta(months=3)）
            → 2026-03-01 出版的书应被保留
        """
        recent = _book(douban_id="m1", title="近3月内", published=date(2026, 3, 1))
        older = _book(douban_id="m2", title="3月前", published=date(2026, 2, 15))
        orch.store.save_book(recent)
        orch.store.save_book(older)

        books = orch._load_books_from_store(months=3)
        titles = {b.title for b in books}
        assert "近3月内" in titles
        assert "3月前" not in titles
