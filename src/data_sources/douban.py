from playwright.sync_api import sync_playwright
import re
import logging
from datetime import date
from typing import List, Optional

from ..models.book import Book

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.WARNING)


class DoubanBookSource:
    """豆瓣读书数据源 - 使用 Playwright 抓取"""

    BASE_URL = "https://book.douban.com"

    def __init__(self, timeout: int = 30000):
        self.timeout = timeout

    def fetch_new_books(self, months: int = 6) -> List[Book]:
        """获取近 N 个月的新书"""
        books = []
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(f'{self.BASE_URL}/latest', wait_until='networkidle', timeout=self.timeout)

            items = page.locator('.chart-dashed-list li.media').all()

            for item in items:
                book = self._parse_item(item)
                if book and self._is_recent(book.published_date, months):
                    books.append(book)

            browser.close()

        return books

    def _parse_item(self, item) -> Optional[Book]:
        try:
            # 书名和链接
            title_elem = item.locator('h2 a')
            title = title_elem.inner_text().strip()
            douban_url = title_elem.get_attribute('href')

            # 出版信息
            abstract = item.locator('.subject-abstract').inner_text().strip()
            parts = [p.strip() for p in abstract.split('/')]
            author = parts[0] if len(parts) > 0 else '未知'

            # 解析日期
            pub_date_str = parts[1] if len(parts) > 1 else ''
            date_match = re.search(r'(\d{4})-(\d{1,2})', pub_date_str)
            if date_match:
                pub_date = date(int(date_match.group(1)), int(date_match.group(2)), 1)
            else:
                pub_date = date.today()

            publisher = parts[2] if len(parts) > 2 else '未知'

            # 评分
            rating_text = item.locator('.subject-rating .font-small').inner_text().strip()
            rating = float(rating_text) if rating_text else 0.0

            # 评价人数
            rating_count_text = item.locator('.subject-rating .color-gray').inner_text().strip()
            count_match = re.search(r'(\d+)', rating_count_text)
            rating_count = int(count_match.group(1)) if count_match else 0

            # 类别
            category = self._infer_category(title, abstract)

            return Book(
                title=title,
                author=author,
                publisher=publisher,
                published_date=pub_date,
                rating=rating,
                rating_count=rating_count,
                category=category,
                douban_url=douban_url
            )
        except Exception as e:
            logger.warning(f"解析书籍条目失败: {e}")
            return None

    def _is_recent(self, pub_date: date, months: int) -> bool:
        """判断是否在近 N 个月内"""
        from datetime import timedelta
        cutoff = date.today().replace(day=1) - timedelta(days=30 * months)
        return pub_date >= cutoff

    def _infer_category(self, title: str, abstract: str) -> str:
        """推断书籍类别（基于关键词权重匹配）"""
        # 标题匹配权重更高
        title_text = title.lower()
        abstract_text = abstract.lower()

        categories = {
            '文学': {
                'keywords': ['小说', '散文', '诗', '文学', '诗歌', '随笔', '杂文', '戏剧', '文学理论', '外国文学', '中国文学', '名著', '绘本', '漫画'],
                'weight': 1.5  # 标题中命中权重更高
            },
            '社科': {
                'keywords': ['历史', '哲学', '社会', '心理', '经济', '政治', '法律', '文化', '人类学', '社会学', '经济学', '管理', '传播', '新闻'],
                'weight': 1.5
            },
            '科技': {
                'keywords': ['编程', '算法', '数据', '技术', '计算机', '编程语言', 'python', 'java', 'javascript', '人工智能', 'AI', '机器学习', '深度学习', '软件', '代码', '架构', '数据库', '网络', '安全', '黑客', '数学', '物理', '科学'],
                'weight': 1.5
            },
            '生活': {
                'keywords': ['生活', '健康', '旅行', '美食', '烹饪', '食谱', '健身', '瑜伽', '心理', '情感', '两性', '育儿', '亲子', '宠物', '家居', '手工', 'DIY'],
                'weight': 1.2
            },
            '童书': {
                'keywords': ['儿童', '绘本', '童话', '少儿', '青少年', '儿童文学', '图画书', '益智', '早教'],
                'weight': 1.5
            },
        }

        best_category = "其他"
        best_score = 0

        for cat, config in categories.items():
            score = 0
            for kw in config['keywords']:
                kw_lower = kw.lower()
                # 标题命中权重更高
                if kw_lower in title_text:
                    score += config['weight']
                elif kw_lower in abstract_text:
                    score += 1.0

            if score > best_score:
                best_score = score
                best_category = cat

        return best_category

    def fetch_book_detail(self, book: Book) -> Book:
        """获取书籍详情（简介和目录）"""
        if not book.douban_url:
            return book

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            try:
                page.goto(book.douban_url, timeout=60000)
                page.wait_for_timeout(2000)

                # 简介
                intro_locator = page.locator('#link-report .intro')
                if intro_locator.count() > 0:
                    intro = intro_locator.first.inner_text()
                    import re
                    intro = re.sub(r'[（(]\s*展开全部\s*[）)]', '', intro)
                    intro = re.sub(r'\s+', ' ', intro).strip()
                    book.description = intro[:1000] if len(intro) > 1000 else intro

                # 目录
                dir_locator = page.locator('[id*="dir"]')
                if dir_locator.count():
                    catalog = page.evaluate('''() => {
                        const dirShort = document.querySelector('[id*="dir"]:not([id*="full"])');
                        if (!dirShort) return '';
                        const dirId = dirShort.id.replace('_short', '');
                        const fullEl = document.getElementById(dirId + '_full');
                        const moreLink = dirShort.querySelector ? dirShort.querySelector('a[href*="javascript"]') : null;
                        if (fullEl) fullEl.style.display = 'block';
                        if (moreLink) moreLink.click();
                        return fullEl ? fullEl.innerText : (dirShort.innerText || '');
                    }''')
                    book.catalog = catalog if catalog else ""
            except Exception as e:
                logger.warning(f"获取书籍详情失败 {book.douban_url}: {e}")

            browser.close()

        return book
