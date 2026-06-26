import pytest

from src.data_sources.douban import DoubanBookSource


class TestInferCategory:
    @pytest.fixture
    def source(self):
        return DoubanBookSource()

    def test_ai_keyword_case_sensitive(self, source):
        assert source._infer_category("AI Revolution", "") == "科技"

    def test_ai_keyword_lowercase(self, source):
        assert source._infer_category("ai revolution", "") == "科技"

    def test_ai_keyword_mixed_case(self, source):
        assert source._infer_category("Ai in Business", "") == "科技"

    def test_chinese_keyword_ml(self, source):
        assert source._infer_category("机器学习实战", "") == "科技"

    def test_chinese_keyword_programming(self, source):
        assert source._infer_category("Python编程从入门到实践", "") == "科技"

    def test_chinese_keyword_deep_learning(self, source):
        assert source._infer_category("深度学习", "") == "科技"

    def test_literature_novel(self, source):
        assert source._infer_category("小说", "") == "文学"

    def test_literature_poem(self, source):
        assert source._infer_category("诗歌集", "") == "文学"

    def test_literature_essay(self, source):
        assert source._infer_category("随笔录", "") == "文学"

    def test_fallback_unknown(self, source):
        assert source._infer_category("完全无关", "") == "其他"

    def test_fallback_abstract_match(self, source):
        assert source._infer_category("一些内容", "人工智能算力") == "科技"

    def test_title_beats_abstract_one_keyword_each(self, source):
        assert source._infer_category("小说", "经济管理") == "文学"
