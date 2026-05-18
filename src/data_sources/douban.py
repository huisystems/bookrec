"""
豆瓣读书数据源

两种抓取策略:
  1. latest: 豆瓣"新书速递"分类页面 (subcat=商业经管)
  2. tag: 豆瓣标签页按时间排序 (tag/人工智能?sort=time)

两种页面结构不同：
  - latest: .chart-dashed-list li.media
  - tag:    .subject-item
"""

import logging
import random
import re
import time
from datetime import date
from typing import List, Optional

from playwright.sync_api import sync_playwright

from ..core.config import (
    FETCH_DELAY_MAX,
    FETCH_DELAY_MIN,
    FETCH_RETRY_TIMES,
    RETRY_DELAYS,
    USER_AGENTS,
)
from ..models.book import Book
from .base import BaseDataSource

logger = logging.getLogger(__name__)

# 只在第一次 import 时配置，防止重复
if not logger.handlers:
    logging.basicConfig(level=logging.WARNING)


class DoubanBookSource(BaseDataSource):
    BASE_URL = "https://book.douban.com"
    LATEST_URL = f"{BASE_URL}/latest"
    TAG_URL = f"{BASE_URL}/tag"

    def __init__(self, timeout: int = 60000):
        self.timeout = timeout

    def _make_browser(self):
        from playwright.sync_api import sync_playwright
        p = sync_playwright().start()
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
        )
        ua = random.choice(USER_AGENTS)
        logger.debug(f"  使用 UA: {ua[:60]}...")
        context = browser.new_context(
            user_agent=ua,
            viewport={"width": 1280, "height": 800},
            locale="zh-CN",
        )
        self._playwright = p
        self._browser = browser
        self._context = context
        return p, browser, context

    def _close_browser(self):
        try:
            if hasattr(self, "_browser") and self._browser:
                self._browser.close()
        except Exception:
            pass
        try:
            if hasattr(self, "_playwright") and self._playwright:
                self._playwright.stop()
        except Exception:
            pass
        self._playwright = None
        self._browser = None
        self._context = None

    def start_session(self):
        """启动一个浏览器会话（复用直到 end_session）"""
        self._session_p = None
        self._session_browser = None
        self._session_context = None
        self._session_page = None

    def _get_page(self):
        """获取当前会话的页面，无会话时自动创建"""
        if hasattr(self, "_session_page") and self._session_page:
            return self._session_page
        p, browser, context = self._make_browser()
        self._session_p = p
        self._session_browser = browser
        self._session_context = context
        self._session_page = context.new_page()
        return self._session_page

    def end_session(self):
        """结束浏览器会话"""
        try:
            if self._session_browser:
                self._session_browser.close()
        except Exception:
            pass
        try:
            if self._session_p:
                self._session_p.stop()
        except Exception:
            pass
        self._session_p = None
        self._session_browser = None
        self._session_context = None
        self._session_page = None

    def _handle_anti_scrape(self, page) -> bool:
        """处理豆瓣反爬页面。返回 True 表示通过了验证"""
        try:
            # 检测常见的反爬/验证码页面特征
            page_title = page.title()
            if any(kw in page_title for kw in ("验证", "captcha", "验证码", "安全验证")):
                logger.warning(f"检测到验证码/反爬页面，标题: {page_title}")
                return False

            # 检测已知的验证码元素
            captcha_selectors = [
                "img[src*='captcha']",
                "img[src*='verify']",
                "#captcha_image",
                ".captcha",
            ]
            for sel in captcha_selectors:
                if page.locator(sel).count() > 0:
                    logger.warning(f"检测到验证码元素: {sel}")
                    return False

            # 原有的"点我继续浏览"检测
            btn = page.get_by_text("点我继续浏览")
            if btn.count() > 0:
                logger.warning("检测到反爬页面，点击继续浏览...")
                btn.click()
                page.wait_for_timeout(3000)
                return True
        except Exception:
            pass
        return False

    def _retry_goto(self, page, url: str, timeout: int | None = None) -> bool:
        """带指数退避重试的页面跳转，返回是否成功"""
        timeout = timeout or self.timeout
        for attempt in range(FETCH_RETRY_TIMES):
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=timeout)
                return True
            except Exception as e:
                logger.warning(
                    f"  页面加载失败 (尝试 {attempt + 1}/{FETCH_RETRY_TIMES}): "
                    f"{url} — {e}"
                )
                if attempt < FETCH_RETRY_TIMES - 1:
                    delay = RETRY_DELAYS[attempt]
                    logger.info(f"  等待 {delay}s 后重试...")
                    time.sleep(delay)
        return False

    def _random_delay(self):
        """请求间随机延迟，降低被反爬标记的风险"""
        delay = random.uniform(FETCH_DELAY_MIN, FETCH_DELAY_MAX)
        logger.debug(f"  随机延迟 {delay:.1f}s")
        time.sleep(delay)

    # ─── 策略 1: latest 新书速递 ────────────────────────

    def fetch_new_books(self, months: int = 12) -> List[Book]:
        return self.fetch_latest(subcat="全部", months=months)

    def fetch_latest(self, subcat: str = "全部", months: int = 12) -> List[Book]:
        url = f"{self.LATEST_URL}?subcat={subcat}"
        logger.info(f"抓取 latest: {url}")

        books = []
        page = self._get_page()

        try:
            if not self._retry_goto(page, url):
                logger.warning(f"latest 页面加载失败: {url}")
                return books
            self._handle_anti_scrape(page)
            page.wait_for_timeout(3000)

            items = page.locator(".chart-dashed-list li.media").all()

            for item in items:
                book = self._parse_latest_item(item)
                if not book:
                    continue
                if self._is_recent(book.published_date, months):
                    book.source_category = subcat
                    books.append(book)
        except Exception as e:
            logger.warning(f"latest 抓取失败: {e}")

        logger.info(f"  -> 抓到 {len(books)} 本")
        return books

    def _parse_latest_item(self, item) -> Optional[Book]:
        """解析 latest 列表中的一条"""
        try:
            title_elem = item.locator("h2 a")
            title = title_elem.inner_text().strip()
            douban_url = title_elem.get_attribute("href")

            abstract = item.locator(".subject-abstract").inner_text().strip()
            parts = [p.strip() for p in abstract.split("/")]
            author = parts[0] if len(parts) > 0 else "未知"

            pub_date_str = parts[1] if len(parts) > 1 else ""
            pub_date = self._parse_date(pub_date_str)

            publisher = parts[2] if len(parts) > 2 else "未知"

            rating_text = (
                item.locator(".subject-rating .font-small").inner_text().strip()
            )
            rating = float(rating_text) if rating_text else 0.0

            # 跳过未评分书籍（豆瓣默认 0.0 表示无评分）
            if rating == 0.0:
                logger.debug(f"  跳过未评分书籍: {title}")
                return None

            rating_count_text = (
                item.locator(".subject-rating .color-gray").inner_text().strip()
            )
            count_match = re.search(r"(\d+)", rating_count_text)
            rating_count = int(count_match.group(1)) if count_match else 0

            return Book(
                title=title,
                author=author,
                publisher=publisher,
                published_date=pub_date,
                rating=rating,
                rating_count=rating_count,
                category=self._infer_category(title, abstract),
                douban_url=douban_url,
                source="douban_latest",
            )
        except Exception as e:
            logger.warning(f"解析 latest 条目失败: {e}")
            return None

    # ─── 策略 2: tag 标签页 ─────────────────────────────

    def fetch_tag_books(
        self, tag: str, months: int = 12, max_pages: int = 3
    ) -> List[Book]:
        books = []
        page_num = 0
        page = self._get_page()

        while page_num < max_pages:
            start = page_num * 20
            url = f"{self.TAG_URL}/{tag}?start={start}&sort=time"
            logger.info(f"  标签 [{tag}] 第 {page_num + 1} 页: {url}")

            if page_num > 0:
                self._random_delay()

            try:
                if not self._retry_goto(page, url):
                    logger.warning(f"  页面加载失败: {url}")
                    break
                self._handle_anti_scrape(page)
                page.wait_for_timeout(2000)
            except Exception as e:
                logger.warning(f"  加载失败: {e}")
                break

            items = page.locator(".subject-item").all()
            if not items:
                break

            page_books = []
            for item in items:
                book = self._parse_tag_item(item)
                if not book:
                    continue
                if self._is_recent(book.published_date, months):
                    book.tags = [tag]
                    page_books.append(book)

            if not page_books:
                logger.info(f"  第 {page_num + 1} 页无近期新书，停止翻页")
                break

            books.extend(page_books)
            page_num += 1

        logger.info(f"  标签 [{tag}] 共抓到 {len(books)} 本")
        return books

    def _parse_tag_item(self, item) -> Optional[Book]:
        try:
            title_elem = item.locator("h2 a")
            if title_elem.count() == 0:
                return None
            title = title_elem.inner_text().strip()
            douban_url = title_elem.get_attribute("href")

            pub_text = item.locator(".pub").inner_text().strip()
            # 格式: 作者 / 译者(可选) / 出版社 / 日期 / 定价
            # 日期总匹配 YYYY-M 格式，从右向左定位
            parts = [p.strip() for p in pub_text.split("/")]
            author = parts[0] if len(parts) > 0 else "未知"

            pub_date_str = ""
            publisher = "未知"
            price = ""

            date_idx = -1
            for i in range(len(parts) - 1, -1, -1):
                if re.search(r"\d{4}-\d{1,2}", parts[i]):
                    date_idx = i
                    break

            if date_idx >= 0:
                pub_date_str = parts[date_idx]
                pub_date = self._parse_date(pub_date_str)
                if date_idx > 1:
                    publisher = parts[date_idx - 1]
                if date_idx + 1 < len(parts):
                    price = parts[date_idx + 1]
            else:
                pub_date = date.today()

            rating = 0.0
            rating_nums = item.locator(".rating_nums")
            if rating_nums.count() > 0:
                rating_text = rating_nums.inner_text().strip()
                if rating_text:
                    rating = float(rating_text)

            # 跳过未评分书籍（豆瓣默认 0.0 表示无评分）
            if rating == 0.0:
                logger.debug(f"  跳过未评分书籍: {title}")
                return None

            pl = item.locator(".pl")
            rating_count = 0
            if pl.count() > 0:
                pl_text = pl.inner_text().strip()
                count_match = re.search(r"(\d+)", pl_text)
                rating_count = int(count_match.group(1)) if count_match else 0

            return Book(
                title=title,
                author=author,
                publisher=publisher,
                published_date=pub_date,
                rating=rating,
                rating_count=rating_count,
                category="AI",
                douban_url=douban_url,
                price=price,
                source="douban_tag",
            )
        except Exception as e:
            logger.warning(f"解析 tag 条目失败: {e}")
            return None

    # ─── 详情页 ────────────────────────────────────────

    def fetch_book_detail(self, book: Book) -> Book:
        if not book.douban_url:
            return book

        page = self._get_page()
        try:
            if not self._retry_goto(page, book.douban_url, timeout=60000):
                logger.warning(f"详情页加载失败: {book.douban_url}")
                return book
            self._handle_anti_scrape(page)
            page.wait_for_timeout(2000)

            intro_locator = page.locator("#link-report .intro")
            if intro_locator.count() > 0:
                intro = intro_locator.first.inner_text()
                intro = re.sub(r"[（(]\s*展开全部\s*[）)]", "", intro)
                intro = re.sub(r"\s+", " ", intro).strip()
                book.description = intro[:1000] if len(intro) > 1000 else intro

            dir_locator = page.locator('[id*="dir"]')
            if dir_locator.count():
                catalog = page.evaluate(
                    """() => {
                    const dirShort = document.querySelector('[id*="dir"]:not([id*="full"])');
                    if (!dirShort) return '';
                    const dirId = dirShort.id.replace('_short', '');
                    const fullEl = document.getElementById(dirId + '_full');
                    const moreLink = dirShort.querySelector ? dirShort.querySelector('a[href*="javascript"]') : null;
                    if (fullEl) fullEl.style.display = 'block';
                    if (moreLink) moreLink.click();
                    return fullEl ? fullEl.innerText : (dirShort.innerText || '');
                }"""
                )
                book.catalog = catalog if catalog else ""
        except Exception as e:
            logger.warning(f"获取详情失败 {book.douban_url}: {e}")

        return book

    # ─── 工具方法 ──────────────────────────────────────

    def _parse_date(self, date_str: str) -> date:
        """解析豆瓣日期格式 '2024-4' 或 '2024-4-30'"""
        date_match = re.search(r"(\d{4})-(\d{1,2})", date_str)
        if date_match:
            return date(
                int(date_match.group(1)),
                int(date_match.group(2)),
                1,
            )
        return date.today()

    def _is_recent(self, pub_date: date, months: int) -> bool:
        from datetime import timedelta

        cutoff = date.today().replace(day=1) - timedelta(days=30 * months)
        return pub_date >= cutoff

    def _infer_category(self, title: str, abstract: str) -> str:
        """推断书籍类别（仅用于 latest 页面）"""
        title_text = title.lower()
        abstract_text = abstract.lower()

        # 所有关键词已归一化为小写，确保对英文关键词（如 "AI"）大小写不敏感
        categories = {
            "文学": {
                "keywords": ["小说", "散文", "诗", "文学", "诗歌", "随笔", "杂文", "戏剧"],
                "weight": 1.5,
            },
            "社科": {
                "keywords": ["历史", "哲学", "社会", "心理", "经济", "政治", "法律", "文化", "人类学"],
                "weight": 1.5,
            },
            "科技": {
                "keywords": ["编程", "算法", "数据", "技术", "计算机", "人工智能", "ai",
                            "机器学习", "深度学习", "软件", "数学", "物理", "科学"],
                "weight": 1.5,
            },
            "生活": {
                "keywords": ["生活", "健康", "旅行", "美食", "健身", "心理", "情感"],
                "weight": 1.2,
            },
        }

        best_category = "其他"
        best_score = 0

        for cat, config in categories.items():
            score = 0
            for kw in config["keywords"]:
                if kw in title_text:
                    score += config["weight"]
                elif kw in abstract_text:
                    score += 1.0

            if score > best_score:
                best_score = score
                best_category = cat

        return best_category
