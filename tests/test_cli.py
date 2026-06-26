"""CLI 端到端测试

不依赖网络：用 CliRunner + 临时 vault 模拟命令行调用。
覆盖所有 8 个命令的 happy path + 关键 error path。
"""

import json
from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from src.cli.app import cli
from src.models.book import Book


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def tmp_vault(tmp_path, monkeypatch):
    """用 tmp_path 作为 vault，并通过 monkeypatch 设置 BOOKREC_VAULT"""
    vault = tmp_path / "vault"
    vault.mkdir()
    monkeypatch.setenv("BOOKREC_VAULT", str(vault))
    return vault


def _make_book(
    douban_id="1234",
    title="测试书",
    author="测试作者",
    rating=8.5,
    rating_count=100,
    category="AI",
    published_year=2026,
    published_month=6,
):
    """构造一个 Book dataclass 用于 mock"""
    return Book(
        title=title,
        author=author,
        publisher="测试出版社",
        published_date=date(published_year, published_month, 1),
        rating=rating,
        rating_count=rating_count,
        category=category,
        douban_url=f"https://book.douban.com/subject/{douban_id}/",
        source="douban_tag",
    )


def _patch_orchestrator(monkeypatch, **overrides):
    """用 MagicMock 替换 Orchestrator，注入预定义行为

    覆盖项：fetch_all, recommend, list_books, search, add_note, stats, history
    """
    mock_orch = MagicMock()
    mock_orch.store.root = "/tmp/fake-vault"
    for key, val in overrides.items():
        setattr(mock_orch, key, val)

    monkeypatch.setattr("src.cli.app.Orchestrator", lambda vault_path: mock_orch)
    return mock_orch


# ─── fetch ──────────────────────────────────────────────


class TestFetch:
    def test_happy_path(self, runner, tmp_vault, monkeypatch):
        mock_orch = _patch_orchestrator(
            monkeypatch,
            fetch_all=MagicMock(
                return_value={"total_fetched": 10, "new": 5, "updated": 2, "duplicates": 3}
            ),
            stats=MagicMock(return_value={"total": 5, "by_category": {"AI": 3, "经管": 2}}),
        )
        result = runner.invoke(cli, ["fetch"])
        assert result.exit_code == 0
        assert "开始抓取" in result.output
        assert "抓取: 10 本" in result.output
        assert "新增: 5 本" in result.output
        mock_orch.fetch_all.assert_called_once()

    def test_invalid_category_skipped_with_warning(self, runner, tmp_vault, monkeypatch):
        _patch_orchestrator(
            monkeypatch,
            fetch_all=MagicMock(
                return_value={"total_fetched": 0, "new": 0, "updated": 0, "duplicates": 0}
            ),
            stats=MagicMock(return_value={"total": 0, "by_category": {}}),
        )
        result = runner.invoke(cli, ["fetch", "-c", "经管,无效分类"])
        assert result.exit_code == 0
        assert "无效分类" in result.output

    def test_all_invalid_exits_zero_no_fetch(self, runner, tmp_vault, monkeypatch):
        mock_orch = _patch_orchestrator(
            monkeypatch,
            fetch_all=MagicMock(
                return_value={"total_fetched": 0, "new": 0, "updated": 0, "duplicates": 0}
            ),
            stats=MagicMock(return_value={"total": 0, "by_category": {}}),
        )
        result = runner.invoke(cli, ["fetch", "-c", "无效1,无效2"])
        assert result.exit_code == 0
        mock_orch.fetch_all.assert_not_called()

    def test_fetch_failure_exits_nonzero(self, runner, tmp_vault, monkeypatch):
        _patch_orchestrator(
            monkeypatch,
            fetch_all=MagicMock(side_effect=RuntimeError("网络炸了")),
        )
        result = runner.invoke(cli, ["fetch"])
        assert result.exit_code != 0
        assert "网络炸了" in result.output


class TestFirstRunCookieHint:
    def test_warns_when_no_cookie_file(self, runner, tmp_vault, monkeypatch, tmp_path):
        fake_cookie = tmp_path / "nonexistent-cookie.json"
        monkeypatch.setattr("src.cli.app.config.COOKIE_FILE", str(fake_cookie))
        _patch_orchestrator(
            monkeypatch,
            fetch_all=MagicMock(
                return_value={"total_fetched": 0, "new": 0, "updated": 0, "duplicates": 0}
            ),
            stats=MagicMock(return_value={"total": 0, "by_category": {}}),
        )
        result = runner.invoke(cli, ["fetch"])
        assert result.exit_code == 0
        assert "未检测到豆瓣登录 cookie" in result.output
        assert "bookrec login" in result.output

    def test_silent_when_cookie_exists(self, runner, tmp_vault, monkeypatch, tmp_path):
        existing_cookie = tmp_path / "cookie.json"
        existing_cookie.write_text("{}")
        monkeypatch.setattr("src.cli.app.config.COOKIE_FILE", str(existing_cookie))
        _patch_orchestrator(
            monkeypatch,
            fetch_all=MagicMock(
                return_value={"total_fetched": 0, "new": 0, "updated": 0, "duplicates": 0}
            ),
            stats=MagicMock(return_value={"total": 0, "by_category": {}}),
        )
        result = runner.invoke(cli, ["fetch"])
        assert result.exit_code == 0
        assert "未检测到豆瓣登录 cookie" not in result.output

    def test_silent_when_cookie_path_empty(self, runner, tmp_vault, monkeypatch):
        monkeypatch.setattr("src.cli.app.config.COOKIE_FILE", "")
        _patch_orchestrator(
            monkeypatch,
            fetch_all=MagicMock(
                return_value={"total_fetched": 0, "new": 0, "updated": 0, "duplicates": 0}
            ),
            stats=MagicMock(return_value={"total": 0, "by_category": {}}),
        )
        result = runner.invoke(cli, ["fetch"])
        assert result.exit_code == 0
        assert "未检测到" not in result.output


class TestRecommend:
    def test_happy_path_stdout(self, runner, tmp_vault, monkeypatch):
        book = _make_book(title="AI 入门", author="作者A")
        _patch_orchestrator(
            monkeypatch,
            recommend=MagicMock(
                return_value={
                    "count": 1,
                    "books": [book],
                    "markdown": "# 推荐\n\n1. AI 入门",
                }
            ),
        )
        result = runner.invoke(cli, ["recommend", "--top", "1"])
        assert result.exit_code == 0
        assert "推荐 TOP 1" in result.output
        assert "AI 入门" in result.output

    def test_empty_result_prints_warning(self, runner, tmp_vault, monkeypatch):
        _patch_orchestrator(
            monkeypatch,
            recommend=MagicMock(return_value={"count": 0, "books": [], "markdown": ""}),
        )
        result = runner.invoke(cli, ["recommend"])
        assert result.exit_code == 0
        assert "没有符合条件的书籍" in result.output

    def test_json_output(self, runner, tmp_vault, monkeypatch):
        book = _make_book(title="测试书", author="作者A")
        _patch_orchestrator(
            monkeypatch,
            recommend=MagicMock(return_value={"count": 1, "books": [book], "markdown": ""}),
        )
        result = runner.invoke(cli, ["recommend", "--json"])
        assert result.exit_code == 0
        # rich console 输出混 ANSI escape，从 output 中切片出 JSON 数组
        data = json.loads(self._extract_json(result.output))
        assert data[0]["title"] == "测试书"
        assert data[0]["author"] == "作者A"

    def test_output_file(self, runner, tmp_vault, tmp_path, monkeypatch):
        out_file = tmp_path / "推荐.md"
        _patch_orchestrator(
            monkeypatch,
            recommend=MagicMock(
                return_value={
                    "count": 1,
                    "books": [_make_book()],
                    "markdown": "# Top 1\n\n1. 测试书",
                }
            ),
        )
        result = runner.invoke(cli, ["recommend", "-o", str(out_file)])
        assert result.exit_code == 0
        assert out_file.exists()
        assert "测试书" in out_file.read_text(encoding="utf-8")

    @staticmethod
    def _extract_json(output: str) -> str:
        start = output.find("[")
        end = output.rfind("]") + 1
        return output[start:end]


class TestListBooks:
    def test_happy_path(self, runner, tmp_vault, monkeypatch):
        _patch_orchestrator(
            monkeypatch,
            list_books=MagicMock(
                return_value=[
                    {
                        "title": "A",
                        "author": "x",
                        "rating": 9.0,
                        "category": "AI",
                        "published": "2026-05",
                        "first_seen": "2026-05-19",
                    },
                ]
            ),
        )
        result = runner.invoke(cli, ["list-books"])
        assert result.exit_code == 0
        assert "A" in result.output

    def test_empty(self, runner, tmp_vault, monkeypatch):
        _patch_orchestrator(
            monkeypatch,
            list_books=MagicMock(return_value=[]),
        )
        result = runner.invoke(cli, ["list-books"])
        assert result.exit_code == 0
        assert "知识库为空" in result.output


class TestSearch:
    def test_happy_path(self, runner, tmp_vault, monkeypatch):
        _patch_orchestrator(
            monkeypatch,
            search=MagicMock(
                return_value=[
                    {"title": "深度学习", "author": "Ian", "rating": 9.0, "category": "AI"},
                ]
            ),
        )
        result = runner.invoke(cli, ["search", "深度学习"])
        assert result.exit_code == 0
        assert "深度学习" in result.output

    def test_no_match(self, runner, tmp_vault, monkeypatch):
        _patch_orchestrator(monkeypatch, search=MagicMock(return_value=[]))
        result = runner.invoke(cli, ["search", "xyznomatch"])
        assert result.exit_code == 0
        assert "未找到匹配" in result.output


class TestNote:
    def test_happy_path(self, runner, tmp_vault, monkeypatch):
        mock_orch = _patch_orchestrator(monkeypatch, add_note=MagicMock())
        result = runner.invoke(cli, ["note", "1234", "我的笔记内容"])
        assert result.exit_code == 0
        assert "笔记已添加" in result.output
        mock_orch.add_note.assert_called_once_with("1234", "我的笔记内容")

    def test_multi_word_joined(self, runner, tmp_vault, monkeypatch):
        mock_orch = _patch_orchestrator(monkeypatch, add_note=MagicMock())
        result = runner.invoke(cli, ["note", "1234", "多词", "笔记", "内容"])
        assert result.exit_code == 0
        mock_orch.add_note.assert_called_once_with("1234", "多词 笔记 内容")

    def test_value_error_exits_nonzero(self, runner, tmp_vault, monkeypatch):
        _patch_orchestrator(
            monkeypatch,
            add_note=MagicMock(side_effect=ValueError("未找到 douban_id=9999 的图书")),
        )
        result = runner.invoke(cli, ["note", "9999", "x"])
        assert result.exit_code == 1
        assert "未找到" in result.output


class TestStats:
    def test_happy_path(self, runner, tmp_vault, monkeypatch):
        _patch_orchestrator(
            monkeypatch,
            stats=MagicMock(return_value={"total": 10, "by_category": {"AI": 4, "经管": 6}}),
        )
        result = runner.invoke(cli, ["stats"])
        assert result.exit_code == 0
        assert "10 本" in result.output
        assert "AI" in result.output
        assert "经管" in result.output


class TestHistory:
    def test_happy_path(self, runner, tmp_vault, monkeypatch):
        _patch_orchestrator(
            monkeypatch,
            history=MagicMock(return_value=["2026-05-top10.md", "2026-04-top10.md"]),
        )
        result = runner.invoke(cli, ["history"])
        assert result.exit_code == 0
        assert "2026-05-top10.md" in result.output
        assert "2026-04-top10.md" in result.output

    def test_empty(self, runner, tmp_vault, monkeypatch):
        _patch_orchestrator(monkeypatch, history=MagicMock(return_value=[]))
        result = runner.invoke(cli, ["history"])
        assert result.exit_code == 0
        assert "暂无推荐历史" in result.output


class TestLogin:
    def test_login_success(self, runner, tmp_vault):
        with patch("src.data_sources.douban.DoubanBookSource.login") as mock_login:
            mock_login.return_value = "/tmp/cookie.json"
            result = runner.invoke(cli, ["login"])
        assert result.exit_code == 0
        mock_login.assert_called_once()

    def test_login_failure_exits_nonzero(self, runner, tmp_vault):
        with patch(
            "src.data_sources.douban.DoubanBookSource.login",
            side_effect=RuntimeError("browser crashed"),
        ):
            result = runner.invoke(cli, ["login"])
        assert result.exit_code != 0
        assert "browser crashed" in result.output


class TestGlobals:
    def test_vault_flag_overrides(self, runner, tmp_path):
        custom_vault = tmp_path / "my-vault"
        custom_vault.mkdir()
        with patch("src.cli.app.Orchestrator") as mock_orch_cls:
            mock_orch = MagicMock()
            mock_orch.stats.return_value = {"total": 0, "by_category": {}}
            mock_orch.store.root = str(custom_vault)
            mock_orch_cls.return_value = mock_orch
            result = runner.invoke(cli, ["--vault", str(custom_vault), "stats"])
        assert result.exit_code == 0
        mock_orch_cls.assert_called_once_with(vault_path=str(custom_vault))

    def test_verbose_flag(self, runner, tmp_vault, monkeypatch):
        _patch_orchestrator(
            monkeypatch,
            stats=MagicMock(return_value={"total": 0, "by_category": {}}),
        )
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["--verbose", "stats"])
        assert result.exit_code == 0


class TestHelp:
    @pytest.mark.parametrize(
        "cmd",
        [
            "fetch",
            "recommend",
            "list-books",
            "search",
            "note",
            "stats",
            "history",
            "login",
        ],
    )
    def test_help(self, runner, cmd):
        result = runner.invoke(cli, [cmd, "--help"])
        assert result.exit_code == 0
        assert "Usage:" in result.output

    def test_top_level_help(self, runner):
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "bookrec" in result.output
        for cmd in [
            "fetch",
            "recommend",
            "list-books",
            "search",
            "note",
            "stats",
            "history",
            "login",
        ]:
            assert cmd in result.output
