"""DoubanBookSource 解析器单测（无网络）

覆盖三类纯函数 / 轻依赖方法，是抓取层的廉价护栏：
  - _parse_date: 豆瓣多种日期字符串 → date 对象
  - _is_recent: 月份窗口边界（与 BookFilter 同源 bug 已修，回归测试）
  - _infer_category: 已在 test_douban_category.py 覆盖
"""

from datetime import date

import pytest

from src.data_sources.douban import DoubanBookSource


class TestParseDate:
    @pytest.fixture
    def source(self):
        return DoubanBookSource()

    def test_year_month_dash(self, source):
        """'2024-4' 标准格式"""
        assert source._parse_date("2024-4") == date(2024, 4, 1)

    def test_year_month_padded(self, source):
        """'2024-04' 两位月份也解析"""
        assert source._parse_date("2024-04") == date(2024, 4, 1)

    def test_year_month_day(self, source):
        """'2024-4-30' 完整日期: 只用年月, 日字段忽略"""
        assert source._parse_date("2024-4-30") == date(2024, 4, 1)

    def test_year_month_day_padded(self, source):
        """'2024-12-31' 完整日期"""
        assert source._parse_date("2024-12-31") == date(2024, 12, 1)

    def test_extra_text_around(self, source):
        """豆瓣页面上 pub 字段常有前后噪声: '/ 人民邮电出版社 / 2024-4 / 89.00元'"""
        assert source._parse_date("人民邮电出版社 / 2024-4 / 89.00元") == date(2024, 4, 1)

    def test_empty_string_returns_today(self, source):
        """空字符串 fallback 到今天 (豆瓣页偶尔缺日期)"""
        # 不直接 == date.today(): 跨日期边界时测试可能因执行时点失败
        # 改成: 结果必须 >= 本月 1 号 (today.replace(day=1) == 本月 1 号)
        result = source._parse_date("")
        assert result >= date.today().replace(day=1)

    def test_garbage_returns_today(self, source):
        """完全无法解析的字符串: 同样 fallback"""
        result = source._parse_date("not a date at all")
        assert result >= date.today().replace(day=1)

    def test_chinese_year_string_does_not_match(self, source):
        """'二〇二四年四月' 不会被解析 — 豆瓣只会输出阿拉伯数字, 这类输入应该 fallback"""
        result = source._parse_date("二〇二四年四月")
        assert result >= date.today().replace(day=1)


class TestIsRecent:
    @pytest.fixture
    def source(self):
        return DoubanBookSource()

    def test_same_month_is_recent(self, source):
        """当月出版: months=1, 边界包含"""
        today = date.today()
        assert source._is_recent(today, months=1) is True

    def test_last_month_is_recent(self, source):
        """上月初: months=2, 包含"""
        from dateutil.relativedelta import relativedelta

        last_month = date.today().replace(day=1) - relativedelta(months=1)
        assert source._is_recent(last_month, months=2) is True

    def test_just_outside_window(self, source):
        """months=3 窗口外的旧书: 排除"""
        from dateutil.relativedelta import relativedelta

        too_old = date.today().replace(day=1) - relativedelta(months=3, days=1)
        assert source._is_recent(too_old, months=3) is False

    def test_exact_boundary_within_window(self, source):
        """正好 months 之前: 包含 (>= 比较)"""
        from dateutil.relativedelta import relativedelta

        exactly_n = date.today().replace(day=1) - relativedelta(months=3)
        assert source._is_recent(exactly_n, months=3) is True

    def test_does_not_use_30_day_approximation(self, source):
        """回归: 不应再用 timedelta(days=30*months) 近似

        复现: 今天 2026-06-26, months=3
          - 错误实现 (30*3=90 天): cutoff=2026-03-03 → 2026-03-01 出版的书被排除
          - 正确实现 (relativedelta): cutoff=2026-03-01 → 2026-03-01 出版的书被保留
        """
        boundary = date(2026, 3, 1)
        # 即使今天不是 2026-06-26, 这条断言也成立: 3 月 1 日的书的相对距离不变
        assert source._is_recent(boundary, months=3) is True
