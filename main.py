#!/usr/bin/env python3
"""
书籍推荐自动化工具
数据来源：豆瓣读书（使用 Playwright 抓取）
"""

import sys
from datetime import date

sys.path.insert(0, './src')

from src.data_sources.douban import DoubanBookSource
from src.services.filter import BookFilter, BookRanker
from src.output.markdown_gen import MarkdownGenerator


def main():
    print("=" * 50)
    print("📚 书籍推荐自动化工具")
    print("=" * 50)

    # 1. 抓取豆瓣数据
    print("\n[1/4] 正在从豆瓣抓取新书数据...")
    source = DoubanBookSource()

    try:
        books = source.fetch_new_books(months=6)
        print(f"    抓取到 {len(books)} 本候选书籍")
    except Exception as e:
        print(f"    抓取失败: {e}")
        return

    if not books:
        print("    未能获取任何书籍数据")
        return

    # 2. 筛选（放宽条件：新书评价人数少，降低阈值）
    print("\n[2/4] 筛选书籍（评分≥7.0，评价≥20人）...")
    book_filter = BookFilter(max_months=6, min_rating=7.0, min_rating_count=20)
    filtered = book_filter.filter(books)
    print(f"    筛选后剩余 {len(filtered)} 本")

    if not filtered:
        print("    筛选后无书籍（近期出版的高分书较少）")
        return

    # 3. 排序
    print("\n[3/4] 综合评分排序...")
    ranker = BookRanker(rating_weight=0.4, recency_weight=0.3, popularity_weight=0.3)
    ranked = ranker.rank(filtered)
    top_books = ranked[:10]
    print(f"    取前 {len(top_books)} 本")

    # 4. 获取详情（简介和目录）
    print("\n[4/4] 获取书籍详情（简介和目录）...")
    for i, book in enumerate(top_books):
        print(f"    [{i+1}/{len(top_books)}] 获取 {book.title[:20]}...")
        source.fetch_book_detail(book)

    # 5. 输出
    print("\n[5/5] 生成推荐列表...")
    generator = MarkdownGenerator()
    output = generator.generate(
        top_books,
        title=f"{date.today().year} 年 {date.today().month} 月书籍推荐 TOP {len(top_books)}"
    )

    output_file = "书籍推荐.md"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(output)
    print(f"    已保存到: {output_file}")

    print("\n" + "=" * 50)
    print("📖 推荐书籍列表")
    print("=" * 50)
    print(output)
    print("\n✅ 完成！")


if __name__ == "__main__":
    main()
