from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional


@dataclass
class Book:
    title: str
    author: str
    publisher: str
    published_date: date
    rating: float
    rating_count: int
    category: str  # "经管" | "AI" | "科学" | ...
    tags: List[str] = field(default_factory=list)  # 豆瓣标签 / 关键词

    # 唯一标识
    isbn: Optional[str] = None
    douban_id: Optional[str] = None
    douban_url: Optional[str] = None
    price: Optional[str] = None

    # 扩展信息
    cover_url: Optional[str] = None
    description: Optional[str] = None
    catalog: Optional[str] = None

    # 元信息
    score: Optional[float] = None  # 综合推荐分
    source: str = "douban_latest"  # 数据来源: douban_latest | douban_tag
    source_category: str = ""      # 抓取时的分类上下文

    def __post_init__(self):
        # 自动从 URL 提取 douban_id
        if self.douban_url and not self.douban_id:
            import re
            m = re.search(r'/subject/(\d+)/?', self.douban_url)
            if m:
                self.douban_id = m.group(1)

    @property
    def rating_display(self) -> str:
        return f"{self.rating:.1f}"

    @property
    def published_display(self) -> str:
        return self.published_date.strftime("%Y-%m")

    @property
    def filename_safe_title(self) -> str:
        """生成适合做文件名的安全标题"""
        import re
        safe = re.sub(r'[\\/:*?"<>|]', '', self.title)
        safe = safe.strip().replace(' ', '')
        return safe[:80] if len(safe) > 80 else safe

    @property
    def category_dir(self) -> str:
        """分类目录名（用于 Obsidian 知识库）"""
        CATEGORY_MAP = {
            "经管": "经管",
            "AI": "AI",
            "科技": "科技",
            "科学": "科学",
            "文学": "文学",
            "社科": "社科",
            "生活": "生活",
            "童书": "童书",
        }
        return CATEGORY_MAP.get(self.category, "其他")
