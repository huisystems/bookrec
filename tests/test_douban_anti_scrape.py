"""DoubanBookSource 的反爬处理与 cookie 加载机制测试

不依赖网络：使用 mock 替换 Playwright Browser/Page，
验证 _handle_anti_scrape 检测到登录跳转页时的行为，
以及 _make_browser 在 cookie 文件存在/不存在时是否传 storage_state。
"""

import logging
from unittest.mock import MagicMock, patch

import pytest

from src.data_sources.douban import DoubanBookSource

# ─── _handle_anti_scrape: 登录跳转页检测 ───────────────────


class TestAntiScrapeLoginRedirect:
    @pytest.fixture
    def source(self):
        return DoubanBookSource()

    def _make_page(self, *, title: str, url: str) -> MagicMock:
        page = MagicMock()
        page.title.return_value = title
        page.url = url
        # captcha selectors + 点我继续浏览: 0 个匹配, 否则 _handle_anti_scrape
        # 会走错误分支并 return False, 掩盖我们要测的登录跳转页路径
        page.locator.return_value.count.return_value = 0
        page.get_by_text.return_value.count.return_value = 0
        return page

    def test_login_redirect_by_title_returns_false(self, source, caplog):
        """页面标题是 '豆瓣 - 登录跳转页' 时应检测到登录拦截, 返回 False"""
        page = self._make_page(
            title="豆瓣 - 登录跳转页",
            url="https://accounts.douban.com/...",
        )

        with caplog.at_level(logging.WARNING):
            result = source._handle_anti_scrape(page)

        assert result is False
        assert "登录拦截" in caplog.text

    def test_login_redirect_when_cookie_configured_says_relogin(self, source, tmp_path, caplog):
        """cookie 文件存在但仍被拦截 → 错误日志应提示 '重新跑 login'"""
        cookie = tmp_path / "storage.json"
        cookie.write_text("{}")

        page = self._make_page(
            title="豆瓣 - 登录跳转页",
            url="https://accounts.douban.com/...",
        )

        with (
            patch("src.data_sources.douban.config.COOKIE_FILE", str(cookie)),
            caplog.at_level(logging.ERROR),
        ):
            result = source._handle_anti_scrape(page)

        assert result is False
        assert "已失效" in caplog.text or "重新跑" in caplog.text

    def test_login_redirect_when_no_cookie_says_run_login(self, source, tmp_path, caplog):
        """无 cookie 文件时被拦截 → 错误日志应提示 '跑 bookrec login'"""
        nonexistent = tmp_path / "no-such-cookie.json"
        page = self._make_page(
            title="豆瓣 - 登录跳转页",
            url="https://accounts.douban.com/...",
        )

        with (
            patch("src.data_sources.douban.config.COOKIE_FILE", str(nonexistent)),
            caplog.at_level(logging.ERROR),
        ):
            result = source._handle_anti_scrape(page)

        assert result is False
        assert "bookrec login" in caplog.text


# ─── _make_browser: cookie 加载路径 ────────────────────────


class TestMakeBrowserCookieLoading:
    @pytest.fixture
    def source(self):
        return DoubanBookSource()

    def test_make_browser_without_cookie_does_not_pass_storage_state(
        self,
        source,
        tmp_path,
    ):
        """cookie 文件不存在时, new_context 不应接收 storage_state 参数"""
        nonexistent = tmp_path / "no-cookie.json"
        new_context = MagicMock()
        launcher = MagicMock()
        launcher.chromium.launch.return_value.new_context = new_context
        launcher.new_context = new_context

        with (
            patch("src.data_sources.douban.config.COOKIE_FILE", str(nonexistent)),
            patch("src.data_sources.douban.sync_playwright") as sp,
        ):
            sp.return_value.start.return_value = launcher
            source._make_browser()

        kwargs = new_context.call_args.kwargs
        assert "storage_state" not in kwargs

    def test_make_browser_with_cookie_passes_storage_state(
        self,
        source,
        tmp_path,
    ):
        """cookie 文件存在时, new_context 应接收 storage_state=该路径"""
        cookie = tmp_path / "real-cookie.json"
        cookie.write_text("{}")
        new_context = MagicMock()
        launcher = MagicMock()
        launcher.chromium.launch.return_value.new_context = new_context
        launcher.new_context = new_context

        with (
            patch("src.data_sources.douban.config.COOKIE_FILE", str(cookie)),
            patch("src.data_sources.douban.sync_playwright") as sp,
        ):
            sp.return_value.start.return_value = launcher
            source._make_browser()

        kwargs = new_context.call_args.kwargs
        assert kwargs.get("storage_state") == str(cookie)
