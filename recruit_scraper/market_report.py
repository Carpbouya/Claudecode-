import asyncio
import logging
import os
from datetime import datetime

import aiohttp

from config import HEADERS, DATA_DIR
from storage import (
    search_jobs, get_jobs_without_details, get_jobs_with_details,
    bulk_insert_details, init_db,
)
from worker import Worker
from exporter import export_csv

logger = logging.getLogger(__name__)


async def run_market_report(keyword: str, prefecture: str = "",
                             offer_salary: int | None = None,
                             max_detail_pages: int = 1000):
    init_db()

    listing_jobs = search_jobs(keyword=keyword, prefecture=prefecture)
    if not listing_jobs:
        print(f"\n  該当する求人がDB内に見つかりません。")
        print(f"  先に `python main.py crawl` を実行してください。\n")
        return

    print(f"\n  DB内ヒット: {len(listing_jobs)} 件")

    needs_detail = get_jobs_without_details(
        keyword=keyword, prefecture=prefecture, limit=max_detail_pages
    )

    if needs_detail:
        print(f"  詳細未取得: {len(needs_detail)} 件 → 取得開始...")
        semaphore = asyncio.Semaphore(3)
        connector = aiohttp.TCPConnector(limit=5, force_close=False)
        async with aiohttp.ClientSession(
            headers=HEADERS, connector=connector
        ) as session:
            worker = Worker(0, semaphore, session, delay_min=1.5, delay_max=3.0)
            details = await worker.fetch_details(needs_detail)
            if details:
                bulk_insert_details(details)
                print(f"  詳細取得完了: {len(details)} 件")

    jobs = get_jobs_with_details(keyword=keyword, prefecture=prefecture)
    if not jobs:
        jobs = listing_jobs

    _print_report(jobs, keyword, prefecture, offer_salary)

    os.makedirs(DATA_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_kw = keyword.replace("/", "_").replace(" ", "_")[:30]
    csv_path = export_csv(
        filename=f"market_{safe_kw}_{prefecture or '全国'}_{ts}.csv",
        with_details=bool(get_jobs_with_details(keyword=keyword, prefecture=prefecture)),
    )
    print(f"\n  出力: {csv_path}\n")


def _print_report(jobs: list[dict], keyword: str, prefecture: str,
                   offer: int | None):
    salaries_min = [j["salary_min"] for j in jobs if j.get("salary_min")]
    salaries_max = [j["salary_max"] for j in jobs if j.get("salary_max")]

    pref_label = prefecture or "全国"

    print()
    print("━" * 50)
    print(f"  市場調査レポート")
    print("━" * 50)
    print(f"  検索条件: {keyword} / {pref_label}")
    print(f"  該当求人数: {len(jobs)} 件")

    if salaries_min and salaries_max:
        avg_min = int(sum(salaries_min) / len(salaries_min))
        avg_max = int(sum(salaries_max) / len(salaries_max))
        all_avg = [(lo + hi) / 2 for lo, hi in zip(salaries_min, salaries_max)]
        all_avg.sort()
        median = int(all_avg[len(all_avg) // 2])
        max_salary = max(salaries_max)

        print()
        print("  ■ 年収相場")
        print(f"    平均下限年収: {avg_min:>12,} 円")
        print(f"    平均上限年収: {avg_max:>12,} 円")
        print(f"    中央値:       {median:>12,} 円")
        print(f"    最高提示:     {max_salary:>12,} 円")

        print()
        print("  ■ 年収帯分布")
        bands = _salary_bands(salaries_min)
        max_count = max(bands.values()) if bands else 1
        for band_label, count in sorted(bands.items()):
            bar_len = int(count / max_count * 20)
            bar = "█" * bar_len
            marker = " ← ボリュームゾーン" if count == max(bands.values()) else ""
            print(f"    {band_label}: {bar} {count}件{marker}")

        if offer is not None:
            print()
            print("  ■ ご提示年収の市場ポジション")
            below = sum(1 for s in salaries_min if s > offer)
            percentile = int((1 - below / len(salaries_min)) * 100)
            print(f"    ご提示額:     {offer:>12,} 円")
            print(f"    市場内位置:   下位 {100 - percentile}%")
            if percentile < 30:
                print(f"    → 反響が期待しにくい水準です。")
                recommended = int(sorted(salaries_min)[len(salaries_min) // 3])
                print(f"    → 推奨ライン: {recommended:>12,} 円〜")
            elif percentile < 60:
                print(f"    → 平均的な水準です。条件次第で反響は見込めます。")
            else:
                print(f"    → 競争力のある水準です。反響が期待できます。")

    companies = {}
    for j in jobs:
        name = j.get("company_name", "")
        if name:
            companies[name] = companies.get(name, 0) + 1
    if companies:
        print()
        print("  ■ 主な掲載企業")
        top = sorted(companies.items(), key=lambda x: -x[1])[:10]
        print("    " + ", ".join(f"{c}({n}件)" for c, n in top))

    skills = {}
    for j in jobs:
        rs = j.get("required_skills", "")
        if rs:
            for part in rs.replace("、", ",").replace("／", ",").split(","):
                s = part.strip()
                if s and len(s) < 30:
                    skills[s] = skills.get(s, 0) + 1
    if skills:
        print()
        print("  ■ 頻出する必須要件")
        top_skills = sorted(skills.items(), key=lambda x: -x[1])[:10]
        for s, count in top_skills:
            print(f"    {s}: {count}件")

    print("━" * 50)


def _salary_bands(salaries: list[int]) -> dict[str, int]:
    bands = {}
    for s in salaries:
        band = (s // 1000000) * 100
        label = f"{band:>4}万〜{band+99}万"
        bands[label] = bands.get(label, 0) + 1
    return bands
