from datetime import date

from ..models.book import Book


class MarkdownGenerator:
    """生成 Markdown 格式的书籍推荐列表"""

    def generate(self, books: list[Book], title: str = None) -> str:
        if not title:
            today = date.today()
            title = f"{today.year} 年 {today.month} 月书籍推荐"

        lines = [
            f"# {title}",
            "",
            "> 精选近期出版、评分优秀的经管/AI类好书",
            "",
            "---",
            "",
        ]

        for i, book in enumerate(books, 1):
            lines.append(self._format_book(book, i))
            lines.append("")

        # 尾注
        lines.extend(
            [
                "---",
                "",
                f"*生成日期: {date.today().isoformat()} | 数据来源: 豆瓣读书*",
                "",
            ]
        )

        return "\n".join(lines)

    def _format_book(self, book: Book, rank: int) -> str:
        if book.rating:
            stars = book.rating / 2
            full = int(stars)
            half = 1 if (stars - full) >= 0.25 else 0
            rating_stars = "⭐" * full + ("½" if half else "")
        else:
            rating_stars = ""

        lines = [
            f"## {rank}. 《{book.title}》",
            "",
            f"**作者：** {book.author}",
            f"**出版社：** {book.publisher}",
            f"**出版日期：** {book.published_display}",
        ]

        if book.price:
            lines.append(f"**定价：** {book.price}")

        if book.rating:
            lines.append(
                f"**豆瓣评分：** {book.rating_display} {rating_stars} ({book.rating_count} 人评价)"
            )
        else:
            lines.append(f"**评价：** {book.rating_count} 人评价")

        lines.append(f"**分类：** {book.category}")

        if book.tags:
            lines.append(f"**标签：** {' / '.join(book.tags)}")

        if book.score is not None:
            lines.append(f"**推荐指数：** {book.score:.1f}/100")

        lines.append("")

        if book.douban_url:
            lines.extend(
                [
                    f"**豆瓣链接：** [{book.douban_url}]({book.douban_url})",
                    "",
                ]
            )

        if book.description:
            lines.extend(
                [
                    "<details>",
                    "<summary>📖 简介</summary>",
                    "",
                    book.description,
                    "</details>",
                    "",
                ]
            )

        if book.catalog:
            lines.extend(
                [
                    "<details>",
                    "<summary>📑 目录</summary>",
                    "",
                ]
            )
            for cat_line in book.catalog.split("\n"):
                if cat_line.strip():
                    lines.append(f"> {cat_line}")
            lines.extend(
                [
                    "</details>",
                    "",
                ]
            )

        lines.append("---")
        return "\n".join(lines)
