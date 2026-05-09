"""全局配置"""
import os
from pathlib import Path

# 知识库根目录（默认在项目根目录下的 知识库/）
# 可通过环境变量 BOOKREC_VAULT 覆盖
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_VAULT = str(_PROJECT_ROOT / "知识库")
VAULT_PATH = os.environ.get("BOOKREC_VAULT", DEFAULT_VAULT)

# 抓取配置
FETCH_MONTHS = 12          # 默认抓取近 N 个月出版的书
FETCH_TIMEOUT = 60000      # Playwright 超时（ms）
FETCH_PAGE_LIMIT = 3       # Tag 页最多抓取页数

# 推荐配置
DEFAULT_TOP_N = 10
DEFAULT_MIN_RATING = 7.0
DEFAULT_MIN_RATING_COUNT = 20

# 豆瓣
DOUBAN_BASE = "https://book.douban.com"
DOUBAN_LATEST = f"{DOUBAN_BASE}/latest"
DOUBAN_TAG = f"{DOUBAN_BASE}/tag"

# 有效分类
VALID_CATEGORIES = ["经管", "AI"]
TAG_CATEGORIES = {
    "AI": ["人工智能", "机器学习", "深度学习"],
    "经管": ["经管", "商业", "管理", "投资"],
}
