"""bookrec CLI - 书籍推荐工具"""

import logging

import click
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table

from ..core import config
from ..services.orchestrator import Orchestrator

console = Console()
err_console = Console(stderr=True)

# 关闭 playwright 和 httpx 的调试日志
logging.getLogger().setLevel(logging.WARNING)


@click.group()
@click.option(
    "--vault",
    envvar="BOOKREC_VAULT",
    default=config.VAULT_PATH,
    help=f"知识库路径 (默认: {config.VAULT_PATH})",
    show_default=True,
)
@click.option("--verbose", is_flag=True, help="显示调试日志")
@click.pass_context
def cli(ctx, vault: str, verbose: bool):
    """bookrec - 书籍推荐自动化工具

    从豆瓣抓取经管/AI类好书，沉淀到 Obsidian 知识库。
    """
    if verbose:
        logging.getLogger().setLevel(logging.INFO)
    ctx.ensure_object(dict)
    ctx.obj["orchestrator"] = Orchestrator(vault_path=vault)


@cli.command()
@click.option(
    "--category",
    "-c",
    default="经管,AI",
    help="分类，逗号分隔",
    show_default=True,
)
@click.option(
    "--months",
    "-m",
    default=config.FETCH_MONTHS,
    help="抓取近 N 个月出版的书",
    type=int,
    show_default=True,
)
@click.option("--max-pages", default=2, type=int, help="每个标签最多抓取页数")
@click.option("--no-detail", is_flag=True, help="不获取详情（简介+目录），仅拉取基础信息")
@click.pass_context
def fetch(ctx, category: str, months: int, max_pages: int, no_detail: bool):
    """抓取新书并入库"""
    orch: Orchestrator = ctx.obj["orchestrator"]
    categories = [c.strip() for c in category.split(",") if c.strip()]

    console.print(f"[bold]📚 开始抓取，分类: {', '.join(categories)}，近 {months} 个月[/]")

    # 用 fetch_all 跨分类去重
    valid_cats = [c for c in categories if c in config.VALID_CATEGORIES]
    invalid_cats = [c for c in categories if c not in config.VALID_CATEGORIES]

    for c in invalid_cats:
        err_console.print(
            f"[red]⚠ 无效分类: {c}，跳过 (可选: {', '.join(config.VALID_CATEGORIES)})[/]"
        )

    if not valid_cats:
        return

    try:
        result = orch.fetch_all(categories=valid_cats, months=months, max_pages=max_pages)
        console.print("\n[cyan]结果汇总[/]")
        console.print(f"  抓取: [green]{result['total_fetched']}[/] 本")
        console.print(f"  新增: [green]{result['new']}[/] 本")
        console.print(f"  更新详情: [green]{result['updated']}[/] 本")
        console.print(f"  去重跳过: {result['duplicates']} 本")
    except Exception as e:
        err_console.print(f"[red]  ❌ 抓取失败: {e}[/]")
        raise click.exceptions.Exit(1) from None

    # 显示统计
    console.print("\n[bold]📊 知识库统计[/]")
    stats = orch.stats()
    console.print(f"  图书总数: [green]{stats['total']}[/] 本")
    for cat, count in sorted(stats.get("by_category", {}).items()):
        console.print(f"    {cat}: {count} 本")


@cli.command()
@click.option("--top", "-n", default=config.DEFAULT_TOP_N, type=int, help="推荐数量")
@click.option("--category", "-c", default=None, help="限定分类 (经管/AI)，不传则全部")
@click.option("--min-rating", default=config.DEFAULT_MIN_RATING, type=float, help="最低评分")
@click.option(
    "--min-rating-count",
    default=config.DEFAULT_MIN_RATING_COUNT,
    type=int,
    help="最低评价人数",
)
@click.option("--output", "-o", default=None, help="输出到 Markdown 文件")
@click.option("--json", "json_output", is_flag=True, help="JSON 格式输出")
@click.pass_context
def recommend(
    ctx,
    top: int,
    category: str | None,
    min_rating: float,
    min_rating_count: int,
    output: str | None,
    json_output: bool,
):
    """从知识库生成推荐列表"""
    orch: Orchestrator = ctx.obj["orchestrator"]

    console.print(f"[bold]📖 生成推荐 TOP {top}[/]")
    if category:
        console.print(f"   分类: {category}")
    console.print(f"   条件: 评分 ≥{min_rating}，评价 ≥{min_rating_count} 人")

    result = orch.recommend(
        top_n=top,
        category=category,
        min_rating=min_rating,
        min_rating_count=min_rating_count,
    )

    if not result["books"]:
        err_console.print("[yellow]⚠ 没有符合条件的书籍，请先运行 fetch 抓取数据[/]")
        return

    books = result["books"]
    md_content = result["markdown"]

    # 终端展示
    table = Table(title=f"推荐 TOP {result['count']}")
    table.add_column("#", style="dim")
    table.add_column("书名")
    table.add_column("作者")
    table.add_column("评分", justify="right")
    table.add_column("评价", justify="right")
    table.add_column("分类")
    table.add_column("出版")

    for i, book in enumerate(books, 1):
        table.add_row(
            str(i),
            book.title[:30],
            book.author[:12],
            str(book.rating),
            str(book.rating_count),
            book.category,
            book.published_display,
        )
    console.print(table)

    # 输出文件
    if output:
        import os

        filepath = os.path.abspath(output)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(md_content)
        console.print(f"\n[green]✅ 已保存到: {filepath}[/]")
    elif json_output:
        import json

        data = [
            {
                "title": b.title,
                "author": b.author,
                "rating": b.rating,
                "category": b.category,
            }
            for b in books
        ]
        console.print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        # 打印到终端
        console.print("\n" + "=" * 50)
        console.print(Markdown(md_content))


@cli.command()
@click.option("--category", "-c", default=None, help="限定分类")
@click.option("--min-rating", default=0, type=float, help="最低评分")
@click.option("--tag", default=None, help="按标签筛选")
@click.pass_context
def list_books(ctx, category: str | None, min_rating: float, tag: str | None):
    """浏览知识库中的图书"""
    orch: Orchestrator = ctx.obj["orchestrator"]
    books = orch.list_books(category=category, min_rating=min_rating, tag=tag)

    if not books:
        console.print("[yellow]📭 知识库为空[/]")
        return

    table = Table(title=f"知识库 · {len(books)} 本")
    table.add_column("书名")
    table.add_column("作者")
    table.add_column("评分", justify="right")
    table.add_column("分类")
    table.add_column("出版")
    table.add_column("入库")

    for b in sorted(books, key=lambda x: x.get("rating", 0), reverse=True):
        table.add_row(
            b.get("title", "?")[:30],
            b.get("author", "?")[:12],
            str(b.get("rating", "")),
            b.get("category", ""),
            b.get("published", ""),
            str(b.get("first_seen", ""))[:10],
        )
    console.print(table)


@cli.command()
@click.argument("query")
@click.pass_context
def search(ctx, query: str):
    """全文搜索图书"""
    orch: Orchestrator = ctx.obj["orchestrator"]
    results = orch.search(query)

    if not results:
        console.print(f'[yellow]🔍 未找到匹配 "{query}" 的图书[/]')
        return

    table = Table(title=f"搜索: {query} ({len(results)} 条)")
    table.add_column("书名")
    table.add_column("作者")
    table.add_column("评分", justify="right")
    table.add_column("分类")

    for r in results:
        table.add_row(
            r.get("title", "?")[:40],
            r.get("author", "?")[:12],
            str(r.get("rating", "")),
            r.get("category", ""),
        )
    console.print(table)


@cli.command()
@click.argument("douban_id")
@click.argument("note_text", nargs=-1, required=True)
@click.pass_context
def note(ctx, douban_id: str, note_text: tuple):
    """给图书添加笔记"""
    orch: Orchestrator = ctx.obj["orchestrator"]
    text = " ".join(note_text)
    try:
        orch.add_note(douban_id, text)
        console.print(f"[green]✅ 笔记已添加到 douban_id={douban_id}[/]")
    except ValueError as e:
        err_console.print(f"[red]❌ {e}[/]")
        ctx.exit(1)


@cli.command()
@click.pass_context
def stats(ctx):
    """查看知识库统计"""
    orch: Orchestrator = ctx.obj["orchestrator"]
    s = orch.stats()

    console.print("[bold]📊 知识库统计[/]\n")
    console.print(f"  图书总数: [green]{s['total']}[/] 本\n")

    console.print("  分类分布:")
    for cat, count in sorted(s.get("by_category", {}).items()):
        bar = "█" * count + "░" * max(0, 20 - count)
        console.print(f"    {cat:6s} | {bar} {count}")

    console.print("\n  知识库路径:")
    console.print(f"    {orch.store.root}")


@cli.command()
@click.pass_context
def history(ctx):
    """查看历史推荐记录"""
    orch: Orchestrator = ctx.obj["orchestrator"]
    files = orch.history()

    if not files:
        console.print("[yellow]📭 暂无推荐历史[/]")
        return

    console.print("[bold]📜 推荐历史[/]\n")
    for i, f in enumerate(files, 1):
        console.print(f"  {i}. {f}")


@cli.command()
def login():
    """一次性登录豆瓣，保存 cookie 到本地用于后续抓取"""
    from src.data_sources.douban import DoubanBookSource

    console.print("[bold]🔐 启动豆瓣登录[/]")
    console.print(
        f"cookie 将保存到: [cyan]{config.COOKIE_FILE}[/]\n"
        f"可通过环境变量 [cyan]BOOKREC_COOKIE_FILE[/] 覆盖"
    )
    try:
        DoubanBookSource.login()
    except Exception as e:
        err_console.print(f"[red]登录失败: {e}[/]")
        raise click.exceptions.Exit(1) from None


def main():
    cli(obj={})


if __name__ == "__main__":
    main()
