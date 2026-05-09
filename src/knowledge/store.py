"""Obsidian 知识库存储层

每本书存储为独立 .md 文件，使用 YAML frontmatter 存放结构化数据。
目录结构:
  <root>/
    图书/
      经管/
        书名.md
      AI/
        书名.md
      __索引.md
    推荐列表/
      2026-05-TOP10.md
    统计.md
    数据源快照/
      2026-05-09-经管.json
"""

import json
import os
import re
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

import yaml

from ..models.book import Book


class ObsidianStore:
    def __init__(self, root_path: str):
        self.root = Path(root_path)
        self._ensure_dirs()

    def _ensure_dirs(self):
        for cat in ["经管", "AI", "科技", "科学", "文学", "社科", "生活", "童书", "其他"]:
            (self.root / "图书" / cat).mkdir(parents=True, exist_ok=True)
        (self.root / "推荐列表").mkdir(parents=True, exist_ok=True)
        (self.root / "数据源快照").mkdir(parents=True, exist_ok=True)

    # ─── Book CRUD ───────────────────────────────────────

    def save_book(self, book: Book, notes: str = "") -> bool:
        """保存一本书到知识库。已存在则合并更新。返回 True 表示新增，False 表示更新"""
        filepath = self._book_filepath(book)
        exists = filepath.exists()

        if exists:
            existing = self._load_yaml(filepath)
            first_seen = existing.get("first_seen", date.today().isoformat())
            existing_notes = existing.get("_notes", "")
        else:
            first_seen = date.today().isoformat()
            existing_notes = ""

        merged_notes = notes or existing_notes

        yaml_data = {
            "douban_id": book.douban_id or "",
            "title": book.title,
            "author": book.author,
            "publisher": book.publisher,
            "published": book.published_display,
            "isbn": book.isbn or "",
            "rating": book.rating,
            "rating_count": book.rating_count,
            "category": book.category,
            "tags": book.tags,
            "source": book.source,
            "source_category": book.source_category,
            "first_seen": first_seen,
            "last_seen": date.today().isoformat(),
            "last_recommended": "",
            "price": book.price or "",
            "source_url": book.douban_url or "",
        }

        content = ["---"]
        content.append(yaml.dump(yaml_data, allow_unicode=True, default_flow_style=False).strip())
        content.append("---")
        content.append("")

        if book.description:
            content.append("## 简介")
            content.append("")
            content.append(book.description)
            content.append("")

        if book.catalog:
            content.append("## 目录")
            content.append("")
            for line in book.catalog.split("\n"):
                if line.strip():
                    content.append(f"> {line}")
            content.append("")

        if merged_notes:
            content.append("## 笔记")
            content.append("")
            content.append(merged_notes)
            content.append("")

        filepath.write_text("\n".join(content), encoding="utf-8")
        return not exists

    def load_book(self, douban_id: str) -> Optional[Dict]:
        """按 douban_id 查找并加载书"""
        for f in self.root.glob("图书/**/*.md"):
            if f.name == "__索引.md":
                continue
            data = self._load_yaml(f)
            if data.get("douban_id") == douban_id:
                return data
        return None

    def list_books(
        self,
        category: Optional[str] = None,
        min_rating: float = 0,
        tag: Optional[str] = None,
    ) -> List[Dict]:
        """列出知识库中的书"""
        results = []
        pattern = f"图书/{category}/**/*.md" if category else "图书/**/*.md"
        for f in self.root.glob(pattern):
            if f.name == "__索引.md":
                continue
            data = self._load_yaml(f)
            if data.get("rating", 0) < min_rating:
                continue
            if tag and tag not in data.get("tags", []):
                continue
            results.append(data)
        return results

    def find_by_douban_id(self, douban_id: str) -> Optional[Path]:
        """查找 douban_id 对应的文件路径"""
        for f in self.root.glob("图书/**/*.md"):
            if f.name == "__索引.md":
                continue
            data = self._load_yaml(f)
            if data.get("douban_id") == douban_id:
                return f
        return None

    def get_existing_ids(self) -> Set[str]:
        """获取知识库中所有已有的 douban_id"""
        ids = set()
        for f in self.root.glob("图书/**/*.md"):
            if f.name == "__索引.md":
                continue
            data = self._load_yaml(f)
            if data.get("douban_id"):
                ids.add(data["douban_id"])
        return ids

    def add_note(self, douban_id: str, note_text: str):
        """为指定书添加笔记"""
        filepath = None
        for f in self.root.glob("图书/**/*.md"):
            if f.name == "__索引.md":
                continue
            data = self._load_yaml(f)
            if data.get("douban_id") == douban_id:
                filepath = f
                break

        if not filepath:
            raise ValueError(f"未找到 douban_id={douban_id} 的图书")

        content = filepath.read_text(encoding="utf-8")

        # 如果已有 ## 笔记 节，替换；否则追加
        note_section = f"\n## 笔记\n\n{note_text}\n"
        if re.search(r"^## 笔记", content, re.MULTILINE):
            content = re.sub(
                r"## 笔记\n.*?(?=\n## |\Z)",
                note_section.strip(),
                content,
                flags=re.DOTALL,
            )
        else:
            content = content.rstrip() + "\n\n" + note_section

        filepath.write_text(content, encoding="utf-8")

    # ─── 推荐列表 ────────────────────────────────────────

    def save_recommendation(
        self, title: str, books_data: List[Dict], content: str
    ):
        """保存一份推荐列表"""
        filename = f"{title.replace(' ', '-').replace('/', '-')}.md"
        filepath = self.root / "推荐列表" / filename
        filepath.write_text(content, encoding="utf-8")

        # 同时更新被推荐书的 last_recommended
        today = date.today().isoformat()
        for bd in books_data:
            douban_id = bd.get("douban_id")
            if not douban_id:
                continue
            filepath = self.find_by_douban_id(douban_id)
            if filepath:
                self._update_yaml_field(filepath, "last_recommended", today)

    # ─── 索引和统计 ──────────────────────────────────────

    def generate_index(self) -> str:
        """生成 __索引.md"""
        books = self.list_books()
        lines = ["# 图书索引", "", f"> 共计 {len(books)} 本书", "", "---", ""]

        # 按分类分组
        by_cat: Dict[str, list] = {}
        for b in books:
            cat = b.get("category", "其他")
            by_cat.setdefault(cat, []).append(b)

        for cat in sorted(by_cat.keys()):
            lines.append(f"## {cat}")
            lines.append("")
            lines.append("| # | 书名 | 作者 | 评分 | 出版 | 入库 |")
            lines.append("| --- | --- | --- | --- | --- | --- |")
            for i, b in enumerate(sorted(by_cat[cat], key=lambda x: x.get("rating", 0), reverse=True), 1):
                title = b.get("title", "?")
                author = b.get("author", "?")[:12]
                rating = b.get("rating", 0)
                published = b.get("published", "?")
                first_seen = b.get("first_seen", "?")[:10]
                lines.append(f"| {i} | {title} | {author} | {rating} | {published} | {first_seen} |")
            lines.append("")

        index_path = self.root / "图书" / "__索引.md"
        content = "\n".join(lines)
        index_path.write_text(content, encoding="utf-8")
        return content

    def update_stats(self) -> Dict:
        """生成并保存统计信息，返回统计数据"""
        books = self.list_books()

        total = len(books)
        by_cat: Dict[str, int] = {}
        total_rating = 0.0
        rated_count = 0
        for b in books:
            cat = b.get("category", "其他")
            by_cat[cat] = by_cat.get(cat, 0) + 1
            r = b.get("rating", 0)
            if r > 0:
                total_rating += r
                rated_count += 1

        lines = [
            "# 知识库统计",
            "",
            f"最后更新: {date.today().isoformat()}",
            "",
            "## 总览",
            "",
            f"- 图书总数: {total}",
            f"- 平均评分: {total_rating / rated_count:.2f}" if rated_count else "- 平均评分: N/A",
            "",
            "## 分类分布",
            "",
        ]
        for cat in sorted(by_cat.keys()):
            lines.append(f"- **{cat}**: {by_cat[cat]} 本")
        lines.append("")

        stats_path = self.root / "统计.md"
        stats_path.write_text("\n".join(lines), encoding="utf-8")

        return {"total": total, "by_category": by_cat}

    # ─── 数据源快照 ─────────────────────────────────────

    def save_snapshot(self, category: str, raw_books: List[Dict]):
        """保存原始抓取数据"""
        today = date.today().strftime("%Y-%m-%d")
        filename = f"{today}-{category}.json"
        filepath = self.root / "数据源快照" / filename
        filepath.write_text(
            json.dumps(raw_books, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

    # ─── 内部工具 ────────────────────────────────────────

    def _book_filepath(self, book: Book) -> Path:
        cat_dir = book.category_dir
        return self.root / "图书" / cat_dir / f"{book.filename_safe_title}.md"

    def _load_yaml(self, filepath: Path) -> Dict:
        """读取 .md 文件的 YAML frontmatter"""
        content = filepath.read_text(encoding="utf-8")
        if not content.startswith("---"):
            return {}
        parts = content.split("---", 2)
        if len(parts) < 3:
            return {}
        try:
            return yaml.safe_load(parts[1]) or {}
        except yaml.YAMLError:
            return {}

    def _update_yaml_field(self, filepath: Path, field: str, value: str):
        """更新 YAML frontmatter 中的单个字段"""
        content = filepath.read_text(encoding="utf-8")
        if not content.startswith("---"):
            return

        parts = content.split("---", 2)
        try:
            data = yaml.safe_load(parts[1]) or {}
        except yaml.YAMLError:
            return

        data[field] = value
        new_yaml = yaml.dump(data, allow_unicode=True, default_flow_style=False).strip()

        new_content = f"---\n{new_yaml}\n---{parts[2]}"
        filepath.write_text(new_content, encoding="utf-8")
