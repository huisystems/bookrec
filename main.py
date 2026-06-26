#!/usr/bin/env python3
"""
书籍推荐自动化工具 - 快速入门
使用 Orchestrator 统一抓取+推荐流程
"""

from src.core import config
from src.services.orchestrator import Orchestrator


def main():
    print("=" * 50)
    print("书籍推荐自动化工具")
    print("=" * 50)

    print("\n[1/3] 初始化编排器...")
    orch = Orchestrator()

    print("\n[2/3] 正在从豆瓣抓取数据（分类：经管、AI）...")
    try:
        result = orch.fetch_all(categories=["经管", "AI"], months=config.FETCH_MONTHS)
        print(f"    抓取到 {result['total_fetched']} 本候选书籍")
        print(f"    新增 {result['new']} 本，更新详情 {result['updated']} 本")
    except Exception as e:
        print(f"    抓取失败: {e}")
        return

    print("\n[3/3] 生成推荐列表...")
    print(
        f"    条件：评分 >={config.DEFAULT_MIN_RATING}，评价 >={config.DEFAULT_MIN_RATING_COUNT} 人"
    )
    rec_result = orch.recommend(
        top_n=config.DEFAULT_TOP_N,
        min_rating=config.DEFAULT_MIN_RATING,
        min_rating_count=config.DEFAULT_MIN_RATING_COUNT,
        months=config.FETCH_MONTHS,
    )

    if not rec_result["books"]:
        print("    没有符合条件的书籍")
        return

    top_books = rec_result["books"]

    print(f"\n{'=' * 50}")
    print(f"推荐书籍 TOP {len(top_books)}")
    print(f"{'=' * 50}")
    for i, book in enumerate(top_books, 1):
        print(f"  {i:2d}. {book.title}")
        print(
            f"      作者: {book.author}  |  评分: {book.rating} "
            f"({book.rating_count} 人评价)  |  分类: {book.category}"
        )

    print(f"\n{'=' * 50}")
    print("完成！推荐列表已保存到知识库「推荐列表」目录")
    print(f"   知识库路径: {orch.store.root}")


if __name__ == "__main__":
    main()
