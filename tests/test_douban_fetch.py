"""DoubanBookSource 抓取层单测（mock Playwright，无网络）

覆盖的之前仅靠 smoke_fetch 间接测试的方法：
  - _parse_latest_item: latest 列表条目解析（_infer_category + 评分门槛）
  - _parse_tag_item:    tag 列表条目解析（pub 字段多段拼接 + 硬编码 category="AI"）
  - fetch_latest:       端到端 latest 抓取（含 _retry_goto 失败路径）
  - fetch_tag_books:    端到端 tag 抓取（翻页 + 早期终止）
  - fetch_book_detail:  详情页抓取（description + catalog）
  - _retry_goto:        指数退避（成功 / 全部失败 / 部分失败）
  - fetch_new_books:    对 fetch_latest(subcat="全部") 的薄封装
"""

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from src.data_sources.douban import DoubanBookSource
from src.models.book import Book

# ─── Helpers ──────────────────────────────────────────────


def _make_item(
    *,
    title="测试书",
    author="作者",
    pub="出版社",
    date_str="2024-4",
    rating="8.5",
    rating_count="100 人评价",
    url="https://book.douban.com/subject/1234567/",
    abstract=None,
):
    """构造一个 latest 列表条目 mock"""
    item = MagicMock()
    title_elem = MagicMock()
    title_elem.inner_text.return_value = title
    title_elem.get_attribute.return_value = url
    item.locator.side_effect = lambda sel: _LatestLocator(
        sel,
        {
            "h2 a": title_elem,
            ".subject-abstract": _TextLocator(
                abstract or f"{author} / {pub} / {date_str} / 39.00元"
            ),
            ".subject-rating .font-small": _TextLocator(rating),
            ".subject-rating .color-gray": _TextLocator(rating_count),
        },
    )
    return item


class _TextLocator:
    """Mock 一个 Playwright locator, count()=1, inner_text()=value"""

    def __init__(self, value: str):
        self._value = value

    def count(self):
        return 1 if self._value else 0

    def inner_text(self):
        return self._value


class _LatestLocator:
    """Mock Playwright locator chain, 按 selector 返回子 locator"""

    def __init__(self, selector: str, mapping: dict[str, MagicMock | _TextLocator]):
        self._selector = selector
        self._mapping = mapping

    def __getattr__(self, name):
        if name in ("count", "inner_text", "get_attribute", "all", "first"):
            target = self._mapping.get(self._selector)
            if isinstance(target, _TextLocator):
                if name == "count":
                    return target.count
                if name == "inner_text":
                    return target.inner_text
            if isinstance(target, MagicMock):
                if name == "count":
                    return target.count
                if name == "inner_text":
                    return target.inner_text
                if name == "get_attribute":
                    return target.get_attribute
            if name == "count":
                return lambda: 0
            if name == "all":
                return lambda: []
            if name == "first":
                return self
            return MagicMock()
        raise AttributeError(name)


def _make_tag_item(
    *,
    title="Tag书",
    pub_text="作者 / 出版社 / 2024-4 / 39.00元",
    rating="8.7",
    rating_count="200人评价",
    url="https://book.douban.com/subject/7654321/",
):
    """构造一个 tag 列表条目 mock"""
    item = MagicMock()
    title_elem = MagicMock()
    title_elem.inner_text.return_value = title
    title_elem.get_attribute.return_value = url
    title_elem.count.return_value = 1

    pub_locator = _TextLocator(pub_text)
    rating_locator = _TextLocator(rating)
    pl_locator = _TextLocator(rating_count)

    def locator(sel):
        if sel == "h2 a":
            return title_elem
        if sel == ".pub":
            return pub_locator
        if sel == ".rating_nums":
            return rating_locator
        if sel == ".pl":
            return pl_locator
        empty = _TextLocator("")
        return empty

    item.locator.side_effect = locator
    return item


def _make_page_with_items(items: list, *, title="豆瓣读书", url="https://book.douban.com/"):
    """构造一个 list-items 页面 mock

    page.locator 的语义：
      - 反爬 selector (captcha/verify) → _EmptyLocator
      - items 列表 selector (.chart-dashed-list li.media / .subject-item) → _ItemsLocator
      - 其他 selector → _EmptyLocator
        (让 _parse_latest_item / _parse_tag_item 在 item.locator("h2 a") 链式
         调用时拿不到东西，与真实环境一致)
    """
    page = MagicMock()
    page.title.return_value = title
    page.url = url

    items_selectors = (".chart-dashed-list li.media", ".subject-item")
    anti_selectors = ("captcha", "verify", "登录跳转页")

    def locator(sel):
        if any(kw in sel for kw in anti_selectors):
            return _EmptyLocator()
        if sel in items_selectors:
            return _ItemsLocator(items)
        return _EmptyLocator()

    page.locator.side_effect = locator
    page.get_by_text.return_value.count.return_value = 0
    return page


class _EmptyLocator:
    def count(self):
        return 0

    def all(self):
        return []

    def inner_text(self):
        return ""

    def first(self):
        return self


class _ItemsLocator:
    def __init__(self, items):
        self._items = items

    def all(self):
        return self._items

    def count(self):
        return len(self._items)

    def first(self):
        return self._items[0] if self._items else self


# ─── _parse_latest_item ──────────────────────────────────


class TestParseLatestItem:
    @pytest.fixture
    def source(self):
        return DoubanBookSource()

    def test_basic_book(self, source):
        item = _make_item(
            title="深度学习",
            author="Ian Goodfellow",
            pub="人民邮电出版社",
            date_str="2024-4",
            rating="9.0",
            rating_count="500 人评价",
            abstract="Ian Goodfellow / 人民邮电出版社 / 2024-4 / 168.00元",
        )
        book = source._parse_latest_item(item)
        assert book is not None
        assert book.title == "深度学习"
        assert book.author == "Ian Goodfellow"
        assert book.publisher == "人民邮电出版社"
        assert book.published_date == date(2024, 4, 1)
        assert book.rating == 9.0
        assert book.rating_count == 500
        assert book.douban_url == "https://book.douban.com/subject/1234567/"
        assert book.source == "douban_latest"
        assert book.douban_id == "1234567"

    def test_skips_unrated_book(self, source):
        """rating==0.0 (未评分) 时返回 None"""
        item = _make_item(rating="", rating_count="0 人评价")
        assert source._parse_latest_item(item) is None

    def test_infers_ai_category_from_title(self, source):
        item = _make_item(title="深度学习实战", abstract="机器学习算法")
        book = source._parse_latest_item(item)
        assert book is not None
        assert book.category == "科技"

    def test_infers_default_category(self, source):
        item = _make_item(title="神秘的传说", abstract="一个关于冒险的故事")
        book = source._parse_latest_item(item)
        assert book is not None
        assert book.category == "其他"

    def test_missing_abstract_returns_none(self, source):
        """abstract 元素为空时进入 except 分支返回 None (不抛异常)"""
        item = MagicMock()
        title_elem = MagicMock()
        title_elem.inner_text.side_effect = Exception("missing")
        item.locator.return_value = title_elem
        assert source._parse_latest_item(item) is None


# ─── _parse_tag_item ─────────────────────────────────────


class TestParseTagItem:
    @pytest.fixture
    def source(self):
        return DoubanBookSource()

    def test_basic_tag_book(self, source):
        item = _make_tag_item(
            title="AI 3.0",
            pub_text="Melanie Mitchell / 中信出版社 / 2024-4 / 89.00元",
            rating="8.5",
            rating_count="300人评价",
        )
        book = source._parse_tag_item(item)
        assert book is not None
        assert book.title == "AI 3.0"
        assert book.publisher == "中信出版社"
        assert book.published_date == date(2024, 4, 1)
        assert book.rating == 8.5
        assert book.rating_count == 300
        assert book.price == "89.00元"
        assert book.category == "AI"
        assert book.source == "douban_tag"
        assert book.douban_id == "7654321"

    def test_skips_unrated_tag_book(self, source):
        item = _make_tag_item(rating="", rating_count="0人评价")
        assert source._parse_tag_item(item) is None

    def test_no_date_in_pub_falls_back_to_today(self, source):
        """pub 文本中没有任何 YYYY-M 段 → 出版日期用今天 fallback"""
        item = _make_tag_item(pub_text="无名作者 / 出版社 / 无定价信息")
        book = source._parse_tag_item(item)
        assert book is not None
        assert book.published_date >= date.today().replace(day=1)

    def test_missing_title_returns_none(self, source):
        item = MagicMock()
        empty_title = MagicMock()
        empty_title.count.return_value = 0
        item.locator.side_effect = lambda sel: empty_title if sel == "h2 a" else _TextLocator("")
        assert source._parse_tag_item(item) is None


# ─── _retry_goto ─────────────────────────────────────────


class TestRetryGoto:
    @pytest.fixture
    def source(self):
        return DoubanBookSource()

    def test_success_first_try(self, source):
        page = MagicMock()
        page.goto.return_value = None
        with patch("src.data_sources.douban.time.sleep") as sleep_mock:
            assert source._retry_goto(page, "https://x") is True
        page.goto.assert_called_once()
        sleep_mock.assert_not_called()

    def test_all_attempts_fail(self, source):
        page = MagicMock()
        page.goto.side_effect = Exception("network error")
        with patch("src.data_sources.douban.time.sleep") as sleep_mock:
            assert source._retry_goto(page, "https://x") is False
        assert page.goto.call_count >= 2
        assert sleep_mock.call_count >= 1

    def test_partial_failure_then_success(self, source):
        page = MagicMock()
        page.goto.side_effect = [Exception("net"), Exception("net"), None]
        with patch("src.data_sources.douban.time.sleep"):
            assert source._retry_goto(page, "https://x") is True
        assert page.goto.call_count == 3

    def test_uses_provided_timeout(self, source):
        page = MagicMock()
        page.goto.return_value = None
        source._retry_goto(page, "https://x", timeout=5000)
        kwargs = page.goto.call_args.kwargs
        assert kwargs.get("timeout") == 5000


# ─── fetch_latest 端到端 ─────────────────────────────────


class TestFetchLatest:
    @pytest.fixture
    def source(self):
        return DoubanBookSource()

    def _patch_session(self, source, page):
        source._session_page = page
        return source

    def test_returns_recent_books(self, source):
        recent_month = date.today().strftime("%Y-%m")
        recent_item = _make_item(
            title="新书A",
            abstract=f"作者X / 出版社Y / {recent_month} / 39.00元",
            rating="8.5",
            rating_count="100 人评价",
        )
        old_item = _make_item(
            title="旧书B",
            abstract="作者Z / 出版社W / 2020-1 / 39.00元",
            rating="7.0",
            rating_count="50 人评价",
        )
        page = _make_page_with_items([recent_item, old_item])
        self._patch_session(source, page)

        books = source.fetch_latest(subcat="经管", months=12)
        assert len(books) == 1
        assert books[0].title == "新书A"
        assert books[0].source_category == "经管"

    def test_returns_empty_when_goto_fails(self, source):
        page = MagicMock()
        page.goto.side_effect = Exception("network down")
        page.title.return_value = "豆瓣读书"
        page.url = "https://book.douban.com/"
        page.locator.return_value = _EmptyLocator()
        page.get_by_text.return_value.count.return_value = 0
        self._patch_session(source, page)

        books = source.fetch_latest(subcat="全部", months=12)
        assert books == []

    def test_skips_unparseable_items(self, source):
        recent_month = date.today().strftime("%Y-%m")
        good = _make_item(
            title="好书",
            abstract=f"A / B / {recent_month} / 9.00元",
            rating="8.0",
            rating_count="10 人评价",
        )
        bad = MagicMock()
        bad.locator.side_effect = Exception("layout changed")
        page = _make_page_with_items([good, bad])
        self._patch_session(source, page)

        books = source.fetch_latest(subcat="全部", months=12)
        assert len(books) == 1
        assert books[0].title == "好书"

    def test_fetch_new_books_delegates_to_fetch_latest(self, source):
        """fetch_new_books 应当是 fetch_latest(subcat='全部') 的薄封装"""
        page = _make_page_with_items([])
        self._patch_session(source, page)
        books = source.fetch_new_books(months=6)
        assert books == []


# ─── fetch_tag_books 端到端 ──────────────────────────────


class TestFetchTagBooks:
    @pytest.fixture
    def source(self):
        return DoubanBookSource()

    def _patch_session(self, source, page):
        source._session_page = page
        return source

    def test_returns_recent_books(self, source):
        recent_month = date.today().strftime("%Y-%m")
        item = _make_tag_item(
            title="AI 入门",
            pub_text=f"作者 / 出版社 / {recent_month} / 50.00元",
            rating="8.0",
            rating_count="100人评价",
        )
        page = _make_page_with_items([item])
        self._patch_session(source, page)

        books = source.fetch_tag_books(tag="人工智能", months=12, max_pages=1)
        assert len(books) == 1
        assert books[0].title == "AI 入门"
        assert books[0].tags == ["人工智能"]

    def test_stops_at_empty_page(self, source):
        """第 1 页没数据 → 不再翻页, 返回空列表"""
        page = _make_page_with_items([])
        self._patch_session(source, page)
        with patch("src.data_sources.douban.time.sleep"):
            books = source.fetch_tag_books(tag="冷门标签", max_pages=3)
        assert books == []

    def test_stops_when_no_recent_books(self, source):
        """第 1 页有数据但全部超月份窗口 → 终止 (page_books 为空触发 break)"""
        old = _make_tag_item(
            title="老书",
            pub_text="A / B / 2020-1 / 10.00元",
            rating="8.0",
            rating_count="100人评价",
        )
        page = _make_page_with_items([old])
        self._patch_session(source, page)

        books = source.fetch_tag_books(tag="标签", months=12, max_pages=3)
        assert books == []


# ─── fetch_book_detail ──────────────────────────────────


class TestFetchBookDetail:
    @pytest.fixture
    def source(self):
        return DoubanBookSource()

    def test_no_url_returns_unchanged(self, source):
        book = Book(
            title="x",
            author="y",
            publisher="z",
            published_date=date(2024, 1, 1),
            rating=8.0,
            rating_count=10,
            category="AI",
        )
        result = source.fetch_book_detail(book)
        assert result is book
        assert book.description is None
        assert book.catalog is None

    def test_enriches_with_description(self, source):
        book = Book(
            title="x",
            author="y",
            publisher="z",
            published_date=date(2024, 1, 1),
            rating=8.0,
            rating_count=10,
            category="AI",
            douban_url="https://book.douban.com/subject/1234/",
        )
        page = MagicMock()
        page.goto.return_value = None
        page.title.return_value = "详情"
        page.url = "https://book.douban.com/subject/1234/"

        intro_locator = MagicMock()
        intro_locator.count.return_value = 1
        intro_locator.first.inner_text.return_value = "这是一本好书。 （展开全部）"

        dir_locator = MagicMock()
        dir_locator.count.return_value = 0

        def locator(sel):
            if sel == "#link-report .intro":
                return intro_locator
            return dir_locator

        page.locator.side_effect = locator
        page.get_by_text.return_value.count.return_value = 0
        page.wait_for_timeout = MagicMock()
        page.evaluate.return_value = ""

        source._session_page = page

        result = source.fetch_book_detail(book)
        assert result is book
        assert "展开全部" not in (book.description or "")
        assert "这是一本好书" in book.description

    def test_goto_failure_returns_unchanged(self, source):
        book = Book(
            title="x",
            author="y",
            publisher="z",
            published_date=date(2024, 1, 1),
            rating=8.0,
            rating_count=10,
            category="AI",
            douban_url="https://book.douban.com/subject/1234/",
        )
        page = MagicMock()
        page.goto.side_effect = Exception("net down")
        page.title.return_value = "err"
        page.url = "https://book.douban.com/"
        page.locator.return_value = _EmptyLocator()
        page.get_by_text.return_value.count.return_value = 0

        source._session_page = page

        result = source.fetch_book_detail(book)
        assert result is book
        assert book.description is None
