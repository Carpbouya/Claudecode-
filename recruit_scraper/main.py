#!/usr/bin/env python3
"""
リクルートエージェント求人スクレイパー

使い方:
  # Phase 1: 全国一覧を一括取得
  python main.py crawl --workers 5

  # Phase 2: 市場調査レポート
  python main.py market "1級建築施工管理技士" --prefecture 東京都
  python main.py market "Python" --prefecture 東京都 --offer 5000000

  # DB内検索（詳細取得なし・即時）
  python main.py search "施工管理" --prefecture 東京都

  # CSV/Excelエクスポート
  python main.py export --format csv
  python main.py export --format excel
"""

import argparse
import asyncio
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from storage import init_db, get_job_count, search_jobs
from coordinator import crawl_all
from market_report import run_market_report
from exporter import export_csv, export_excel


def cmd_crawl(args):
    init_db()
    print(f"\n  全国求人一覧クロール開始")
    print(f"  ワーカー数: {args.workers}")
    print(f"  リクエスト間隔: {args.delay_min}-{args.delay_max}秒\n")

    total = asyncio.run(
        crawl_all(
            workers=args.workers,
            delay_min=args.delay_min,
            delay_max=args.delay_max,
            max_pages_per_pref=args.max_pages,
        )
    )
    print(f"\n  完了: {total:,} 件取得、DB総数: {get_job_count():,} 件\n")


def cmd_market(args):
    asyncio.run(
        run_market_report(
            keyword=args.keyword,
            prefecture=args.prefecture,
            offer_salary=args.offer,
            max_detail_pages=args.max_details,
        )
    )


def cmd_search(args):
    init_db()
    jobs = search_jobs(
        keyword=args.keyword,
        prefecture=args.prefecture,
        salary_min=args.salary_min,
    )
    if not jobs:
        print("\n  該当する求人がありません。\n")
        return

    print(f"\n  検索結果: {len(jobs)} 件\n")
    print(f"  {'タイトル':<30} {'企業名':<20} {'年収':>15} {'勤務地':<10}")
    print("  " + "-" * 80)
    for job in jobs[:50]:
        title = (job["title"] or "")[:28]
        company = (job["company_name"] or "")[:18]
        sal = ""
        if job.get("salary_min") and job.get("salary_max"):
            sal = f"{job['salary_min']//10000}万〜{job['salary_max']//10000}万"
        pref = job.get("prefecture") or job.get("location") or ""
        print(f"  {title:<30} {company:<20} {sal:>15} {pref:<10}")

    if len(jobs) > 50:
        print(f"\n  ... 他 {len(jobs) - 50} 件")
    print()


def cmd_export(args):
    init_db()
    count = get_job_count()
    if count == 0:
        print("\n  データがありません。先に crawl を実行してください。\n")
        return

    fmt = args.format
    if fmt == "csv":
        path = export_csv(with_details=args.details)
    elif fmt == "excel":
        path = export_excel(with_details=args.details)
    else:
        path_csv = export_csv(with_details=args.details)
        path_xlsx = export_excel(with_details=args.details)
        print(f"\n  CSV:   {path_csv}")
        print(f"  Excel: {path_xlsx}")
        print(f"  {count:,} 件エクスポート完了\n")
        return

    print(f"\n  {path}")
    print(f"  {count:,} 件エクスポート完了\n")


def cmd_status(_args):
    init_db()
    from config import PREFECTURES
    total = get_job_count()
    print(f"\n  DB総数: {total:,} 件\n")
    if total > 0:
        print(f"  {'都道府県':<8} {'件数':>8}")
        print("  " + "-" * 20)
        for pref in PREFECTURES:
            c = get_job_count(pref)
            if c > 0:
                print(f"  {pref:<8} {c:>8,}")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="リクルートエージェント求人スクレイパー"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="詳細ログ出力"
    )
    sub = parser.add_subparsers(dest="command")

    p_crawl = sub.add_parser("crawl", help="全国求人一覧をクロール")
    p_crawl.add_argument("--workers", "-w", type=int, default=5)
    p_crawl.add_argument("--delay-min", type=float, default=1.5)
    p_crawl.add_argument("--delay-max", type=float, default=3.0)
    p_crawl.add_argument("--max-pages", type=int, default=500)

    p_market = sub.add_parser("market", help="市場調査レポート")
    p_market.add_argument("keyword", help="検索キーワード（資格名など）")
    p_market.add_argument("--prefecture", "-p", default="")
    p_market.add_argument("--offer", type=int, default=None,
                          help="クライアント提示年収（円）")
    p_market.add_argument("--max-details", type=int, default=1000)

    p_search = sub.add_parser("search", help="DB内検索")
    p_search.add_argument("keyword", help="検索キーワード")
    p_search.add_argument("--prefecture", "-p", default="")
    p_search.add_argument("--salary-min", type=int, default=None)

    p_export = sub.add_parser("export", help="CSV/Excelエクスポート")
    p_export.add_argument("--format", "-f", default="csv",
                          choices=["csv", "excel", "both"])
    p_export.add_argument("--details", action="store_true",
                          help="詳細データ付きでエクスポート")

    sub.add_parser("status", help="DB状態確認")

    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    commands = {
        "crawl": cmd_crawl,
        "market": cmd_market,
        "search": cmd_search,
        "export": cmd_export,
        "status": cmd_status,
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
