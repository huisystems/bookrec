"""CLI 端到端测试

不依赖网络：用 CliRunner + 临时 vault 模拟命令行调用，
覆盖 fetch 错误路径的 exit code。
"""

from unittest.mock import MagicMock

import pytest
from click.testing import CliRunner

from src.cli.app import cli


@pytest.fixture
def runner():
    return CliRunner()


def test_fetch_exits_nonzero_on_failure(runner):
    """fetch 命令内部异常时应以非零退出码结束，让 CI/脚本能感知失败"""
    # 注入一个会抛异常的 orchestrator
    from src.services.orchestrator import Orchestrator
    original_init = Orchestrator.__init__

    def boom(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        self.source = MagicMock()
        self.source.fetch_latest.side_effect = RuntimeError("网络炸了")
        self.source.fetch_tag_books.return_value = []
        self.source.start_session = MagicMock()
        self.source.end_session = MagicMock()

    Orchestrator.__init__ = boom
    try:
        result = runner.invoke(cli, ["fetch", "--vault", "/tmp/nonexistent-vault-xyz"])
    finally:
        Orchestrator.__init__ = original_init

    assert result.exit_code != 0, f"expected nonzero exit, got {result.exit_code}\noutput: {result.output}"
