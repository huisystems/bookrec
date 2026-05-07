from datetime import date
from typing import List

from ..models.book import Book


class MarkdownGenerator:
    """生成 Markdown 格式的书籍推荐"""

    def generate(self, books: List[Book], title: str = None) -> str:
        if not title:
            today = date.today()
            title = f"{today.year} 年 {today.month} 月书籍推荐"

        lines = [
            f"# {title}",
            "",
            "> 精选近期出版、评分优秀的优质书籍",
            "",
            "---",
            ""
        ]

        for i, book in enumerate(books, 1):
            lines.append(self._format_book(book, i))
            lines.append("")

        return "\n".join(lines)

    def _format_book(self, book: Book, rank: int) -> str:
        rating_stars = "⭐" * int(book.rating / 2)

        lines = [
            f"## {rank}. 《{book.title}》",
            "",
            f"**作者：** {book.author}",
            f"**出版社：** {book.publisher}",
            f"**出版日期：** {book.published_display}",
            f"**豆瓣评分：** {book.rating_display} {rating_stars} ({book.rating_count} 人评价)",
            f"**分类：** {book.category}",
            "",
        ]

        if book.douban_url:
            lines.append(f"**豆瓣链接：** [{book.douban_url}]({book.douban_url})")
            lines.append("")

        if book.description:
            lines.append("<details>")
            lines.append("<summary>📖 简介</summary>")
            lines.append("")
            lines.append(book.description)
            lines.append("</details>")
            lines.append("")

        if book.catalog:
            lines.append("<details>")
            lines.append("<summary>📑 目录</summary>")
            lines.append("")
            for cat_line in book.catalog.split('\n'):
                if cat_line.strip():
                    lines.append(f"> {cat_line}")
            lines.append("</details>")
            lines.append("")

        lines.append("---")

        return "\n".join(lines)
