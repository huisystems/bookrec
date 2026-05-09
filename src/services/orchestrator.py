"""编排器：协调抓取、入库、推荐全流程"""

import logging
from datetime import date
from typing import Dict, List, Optional

from ..core import config
from ..data_sources.douban import DoubanBookSource
from ..knowledge.store import ObsidianStore
from ..models.book import Book
from ..output.markdown_gen import MarkdownGenerator
from .filter import BookFilter, BookRanker

logger = logging.getLogger(__name__)


class Orchestrator:
    def __init__(
        self,
        vault_path: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        self.store = ObsidianStore(vault_path or config.VAULT_PATH)
        self.source = DoubanBookSource(timeout=timeout or config.FETCH_TIMEOUT)
        self.markdown = MarkdownGenerator()

    # ─── 抓取 ──────────────────────────────────────────

    def fetch(self, category: str, months: int = 12, max_pages: int = 2) -> Dict:
        if category not in config.VALID_CATEGORIES:
            raise ValueError(f"无效分类: {category}，可选: {config.VALID_CATEGORIES}")

        if category == "经管":
            return self._fetch_business(months, max_pages)
        elif category == "AI":
            return self._fetch_ai(months, max_pages)

    def fetch_all(self, categories: List[str], months: int = 12, max_pages: int = 2) -> Dict:
        """抓取多个分类，跨分类去重"""
        all_books = []
        self.source.start_session()
        try:
            for cat in categories:
                if cat == "经管":
                    all_books.extend(self._fetch_business_raw(months, max_pages))
                elif cat == "AI":
                    all_books.extend(self._fetch_ai_raw(months, max_pages))
        finally:
            self.source.end_session()

        return self._dedup_and_store(all_books, category_hint="+".join(categories))

    def _fetch_business(self, months: int, max_pages: int = 2) -> Dict:
        return self._dedup_and_store(
            self._fetch_business_raw(months, max_pages),
            category_hint="经管",
        )

    def _fetch_business_raw(self, months: int, max_pages: int) -> List[Book]:
        books = []
        latest_books = self.source.fetch_latest(subcat="商业经管", months=months)
        for b in latest_books:
            b.category = "经管"
            b.source_category = "经管"
        books.extend(latest_books)

        for tag in ["经管", "商业", "管理", "投资"]:
            tag_books = self.source.fetch_tag_books(
                tag=tag, months=months, max_pages=max_pages
            )
            for b in tag_books:
                b.category = "经管"
                b.source_category = "经管"
            books.extend(tag_books)
        return books

    def _fetch_ai(self, months: int, max_pages: int) -> Dict:
        return self._dedup_and_store(
            self._fetch_ai_raw(months, max_pages),
            category_hint="AI",
        )

    def _fetch_ai_raw(self, months: int, max_pages: int) -> List[Book]:
        books = []
        for tag in ["人工智能", "机器学习", "深度学习"]:
            tag_books = self.source.fetch_tag_books(
                tag=tag, months=months, max_pages=max_pages
            )
            for b in tag_books:
                b.category = "AI"
                b.source_category = "AI"
            books.extend(tag_books)
        return books

    def _dedup_and_store(self, books: List[Book], category_hint: str = "") -> Dict:
        existing_ids = self.store.get_existing_ids()
        new_count = 0
        update_count = 0
        dup_count = 0

        for book in books:
            if not book.douban_id:
                continue

            is_new = book.douban_id not in existing_ids
            needs_detail = False

            if is_new:
                needs_detail = True
            else:
                dup_count += 1
                existing = self.store.load_book(book.douban_id)
                if existing and not existing.get("description"):
                    needs_detail = True

            if needs_detail:
                try:
                    self.source.fetch_book_detail(book)
                except Exception as e:
                    logger.warning(f"获取详情失败 {book.title}: {e}")

            if is_new:
                self.store.save_book(book)
                new_count += 1
                existing_ids.add(book.douban_id)
            elif needs_detail:
                # 更新已存在书的详情：复用原始分类路径，只更新 description/catalog
                existing_path = self.store.find_by_douban_id(book.douban_id)
                if existing_path:
                    existing_data = self.store._load_yaml(existing_path)
                    book.category = existing_data.get("category", book.category)
                    book.source_category = existing_data.get("source_category", book.source_category)
                    self.store.save_book(book)
                    update_count += 1

        # 保存数据源快照（用于追溯）
        snapshot = [
            {
                "douban_id": b.douban_id,
                "title": b.title,
                "author": b.author,
                "rating": b.rating,
                "published": b.published_display,
            }
            for b in books
            if b.douban_id
        ]
        self.store.save_snapshot(category_hint or "all", snapshot)

        # 更新索引和统计
        self.store.generate_index()
        stats = self.store.update_stats()

        result = {
            "total_fetched": len(books),
            "new": new_count,
            "updated": update_count,
            "duplicates": dup_count,
            "stats": stats,
        }
        return result

    # ─── 推荐 ──────────────────────────────────────────

    def recommend(
        self,
        top_n: int = 10,
        category: Optional[str] = None,
        min_rating: float = 7.0,
        min_rating_count: int = 20,
        months: int = 12,
    ) -> Dict:
        """从知识库生成推荐列表"""
        all_books = self._load_books_from_store(
            category=category,
            min_rating=min_rating,
            months=months,
        )

        if not all_books:
            return {"books": [], "markdown": "", "count": 0}

        # 过滤
        book_filter = BookFilter(
            max_months=months,
            min_rating=min_rating,
            min_rating_count=min_rating_count,
        )
        filtered = book_filter.filter(all_books, months=months)

        if not filtered:
            return {"books": [], "markdown": "", "count": 0}

        # 排序
        ranker = BookRanker(
            rating_weight=0.4,
            recency_weight=0.3,
            popularity_weight=0.3,
        )
        ranked = ranker.rank(filtered)
        top_books = ranked[:top_n]

        # 生成 Markdown
        today = date.today()
        md_title = f"{today.year} 年 {today.month} 月书籍推荐 TOP {len(top_books)}"
        md_content = self.markdown.generate(top_books, title=md_title)

        # 保存到知识库
        books_data = [
            {
                "douban_id": b.douban_id,
                "title": b.title,
                "author": b.author,
                "rating": b.rating,
                "rating_count": b.rating_count,
                "category": b.category,
            }
            for b in top_books
        ]
        self.store.save_recommendation(md_title, books_data, md_content)

        # 更新索引和统计
        self.store.generate_index()
        self.store.update_stats()

        return {"books": top_books, "markdown": md_content, "count": len(top_books)}

    def _load_books_from_store(
        self,
        category: Optional[str] = None,
        min_rating: float = 0,
        months: int = 12,
    ) -> List[Book]:
        """从知识库加载书数据为 Book 对象"""
        from datetime import timedelta

        raw_list = self.store.list_books(category=category, min_rating=min_rating)
        cutoff = date.today().replace(day=1) - timedelta(days=30 * months)

        seen_ids = set()
        books = []
        for raw in raw_list:
            douban_id = raw.get("douban_id", "")
            if douban_id and douban_id in seen_ids:
                continue
            if douban_id:
                seen_ids.add(douban_id)

            try:
                pub_date = self._parse_date(raw.get("published", ""))
                if pub_date < cutoff:
                    continue
                book = Book(
                    title=raw.get("title", ""),
                    author=raw.get("author", ""),
                    publisher=raw.get("publisher", ""),
                    published_date=pub_date,
                    rating=float(raw.get("rating", 0)),
                    rating_count=int(raw.get("rating_count", 0)),
                    category=raw.get("category", "其他"),
                    tags=raw.get("tags", []),
                    douban_id=douban_id,
                    douban_url=raw.get("source_url", ""),
                    isbn=raw.get("isbn", ""),
                    score=float(raw["score"]) if raw.get("score") else None,
                    source="knowledge_base",
                )
                books.append(book)
            except Exception as e:
                logger.warning(f"加载图书失败: {e}")

        return books

    def _parse_date(self, date_str: str) -> date:
        import re
        m = re.search(r"(\d{4})-(\d{1,2})", str(date_str))
        if m:
            return date(int(m.group(1)), int(m.group(2)), 1)
        return date.today()

    # ─── 知识库查询 ────────────────────────────────────

    def list_books(
        self,
        category: Optional[str] = None,
        min_rating: float = 0,
        tag: Optional[str] = None,
    ) -> List[Dict]:
        return self.store.list_books(category=category, min_rating=min_rating, tag=tag)

    def search(self, query: str) -> List[Dict]:
        """全文搜索图书"""
        results = []
        for f in self.store.root.glob("图书/**/*.md"):
            if f.name == "__索引.md":
                continue
            content = f.read_text(encoding="utf-8")
            if query.lower() in content.lower():
                data = self.store._load_yaml(f)
                if data:
                    results.append(data)
        return results

    def add_note(self, douban_id: str, note_text: str):
        self.store.add_note(douban_id, note_text)

    def stats(self) -> Dict:
        return self.store.update_stats()

    def history(self) -> List[str]:
        """列出历史推荐列表"""
        rec_dir = self.store.root / "推荐列表"
        if not rec_dir.exists():
            return []
        files = sorted(rec_dir.glob("*.md"), reverse=True)
        return [f.name for f in files]
