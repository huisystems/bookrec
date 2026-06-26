"""全局配置"""

import os
from pathlib import Path

# 知识库根目录（默认在项目根目录下的 知识库/）
# 可通过环境变量 BOOKREC_VAULT 覆盖
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_VAULT = str(_PROJECT_ROOT / "知识库")
VAULT_PATH = os.environ.get("BOOKREC_VAULT", DEFAULT_VAULT)

# 抓取配置
FETCH_MONTHS = 12  # 默认抓取近 N 个月出版的书
FETCH_TIMEOUT = 60000  # Playwright 超时（ms）
FETCH_PAGE_LIMIT = 3  # Tag 页最多抓取页数

# 推荐配置
DEFAULT_TOP_N = 10
DEFAULT_MIN_RATING = 7.0
DEFAULT_MIN_RATING_COUNT = 20

# 抓取重试与延迟配置
FETCH_RETRY_TIMES = 3
RETRY_DELAYS = [1, 3, 7]  # 指数退避延迟（秒）
FETCH_DELAY_MIN = 2  # 请求间最小随机延迟（秒）
FETCH_DELAY_MAX = 5  # 请求间最大随机延迟（秒）

# User-Agent 轮换池
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36",
]

# 豆瓣
DOUBAN_BASE = "https://book.douban.com"
DOUBAN_LATEST = f"{DOUBAN_BASE}/latest"
DOUBAN_TAG = f"{DOUBAN_BASE}/tag"

# 豆瓣登录 cookie storage 路径（Playwright storage_state JSON 格式）
# 可通过环境变量 BOOKREC_COOKIE_FILE 覆盖
# 用户通过 'bookrec login' 子命令生成
_DEFAULT_COOKIE_FILE = Path.home() / ".config" / "bookrec" / "douban_storage.json"
COOKIE_FILE = os.environ.get("BOOKREC_COOKIE_FILE", str(_DEFAULT_COOKIE_FILE))

# 有效分类
VALID_CATEGORIES = ["经管", "AI"]
TAG_CATEGORIES = {
    "AI": ["人工智能", "机器学习", "深度学习"],
    "经管": ["经管", "商业", "管理", "投资"],
}
