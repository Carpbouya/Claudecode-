"""
r-agent 求人スクレイパー
========================
前提:
  - pip install playwright pandas openpyxl
  - playwright install chromium

実行:
  python scraper_ragent.py

設定は下の CONFIG セクションだけ変更すればOK。
出力ファイルはそのまま csv_to_excel.py / v4 処理に流せる形式。
"""

import asyncio
import json
import re
import time
import random
from pathlib import Path
from datetime import datetime

import pandas as pd
from playwright.async_api import async_playwright, TimeoutError as PWTimeout

# ─────────────────────────────────────────────
# CONFIG  ← ここだけ変更
# ─────────────────────────────────────────────
EMAIL    = "your_email@example.com"   # r-agentログインメール
PASSWORD = "your_password"            # パスワード

# 検索したい職種キーワード（複数ある場合はリストで）
SEARCH_KEYWORDS = [
    "建築施工管理",
    "土木施工管理",
    "設備施工管理",
    "建築営業",
    "不動産開発",
]

MAX_PAGES = 10        # 各キーワードの最大ページ数（1ページ約20件）
DELAY_MIN = 1.5       # リクエスト間の最小待機秒
DELAY_MAX = 3.0       # リクエスト間の最大待機秒
OUTPUT_FILE = f"ragent_scrape_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
HEADLESS = False      # True にすると画面非表示（デバッグ時は False 推奨）
# ─────────────────────────────────────────────

LOGIN_URL  = "https://www.r-agent.com/login/"
SEARCH_URL = "https://www.r-agent.com/job/search/?keyword={keyword}&pg={page}"


def sleep_random():
    time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))


async def login(page):
    print("  ログイン中...")
    await page.goto(LOGIN_URL, wait_until="networkidle")
    await page.fill('input[type="email"], input[name="email"]', EMAIL)
    await page.fill('input[type="password"], input[name="password"]', PASSWORD)
    await page.click('button[type="submit"], input[type="submit"]')
    await page.wait_for_load_state("networkidle")
    print("  ログイン完了")


async def scrape_list_page(page, url) -> list[str]:
    """一覧ページから求人詳細URLを収集"""
    await page.goto(url, wait_until="networkidle")
    await asyncio.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

    # 求人カードのリンクを抽出（セレクタはサイト構造に合わせて調整）
    links = await page.eval_on_selector_all(
        'a[href*="/job/detail/"], a[href*="/job/view/"]',
        "els => els.map(e => e.href)"
    )
    return list(set(links))


async def scrape_detail_page(page, url: str) -> dict | None:
    """詳細ページからデータ抽出"""
    try:
        await page.goto(url, wait_until="networkidle")
        await asyncio.sleep(random.uniform(DELAY_MIN, DELAY_MAX))
    except PWTimeout:
        print(f"    タイムアウト: {url}")
        return None

    async def get_text(selectors: list[str]) -> str:
        for sel in selectors:
            try:
                el = await page.query_selector(sel)
                if el:
                    return (await el.inner_text()).strip()
            except Exception:
                pass
        return ""

    async def get_all_text(selectors: list[str]) -> str:
        for sel in selectors:
            try:
                els = await page.query_selector_all(sel)
                if els:
                    texts = [await e.inner_text() for e in els]
                    return "\n".join(t.strip() for t in texts if t.strip())
            except Exception:
                pass
        return ""

    # ─── セレクタ（実際のDOM構造に合わせて調整が必要） ───
    company = await get_text([
        '.company-name', '.corp-name', '[class*="company"]',
        'h2.company', '.job-company'
    ])
    title = await get_text([
        'h1.job-title', '.job-title', 'h1[class*="title"]',
        '.position-name', '.recruit-title'
    ])
    employment_type = await get_text([
        '.employment-type', '[class*="employ"]', 'td:has-text("雇用形態") + td'
    ])
    location = await get_text([
        '.work-location', '[class*="location"]', 'td:has-text("勤務地") + td',
        '.job-location'
    ])
    salary_type = await get_text([
        '.salary-type', 'td:has-text("給与形態") + td',
        '[class*="salary-type"]'
    ])
    salary_amount = await get_text([
        '.salary-amount', '.salary', 'td:has-text("給与") + td',
        '[class*="salary"]'
    ])
    keywords = await get_all_text([
        '.tags', '.keywords', '.conditions', '[class*="tag"]',
        '.job-tag'
    ])
    content = await get_text([
        '.job-description', '.work-content', 'td:has-text("仕事内容") + td',
        '[class*="description"]', '.recruit-detail'
    ])
    requirements = await get_text([
        '.requirements', '.qualification', 'td:has-text("必須") + td',
        '[class*="require"]', '.apply-condition'
    ])

    # フルテキストフォールバック（セレクタが合わない場合の保険）
    if not company and not title:
        # ページ全体のテキストからパターン抽出を試みる
        body_text = await page.inner_text('body')
        print(f"    WARNING: セレクタ未ヒット。ページ確認推奨: {url}")
        # ここにサイト固有のパース処理を追加できる

    return {
        'URL':       url,
        'タイプ':    employment_type or None,
        '名前':      company or None,
        'タイトル':  title or None,
        '給与':      salary_type or None,
        '給与2':     salary_amount or None,
        '場所':      location or None,
        'キーワード': keywords or None,
        'コンテンツ': content or None,
        'コンテンツ5': requirements or None,
    }


async def check_next_page_exists(page) -> bool:
    """次ページリンクが存在するか確認"""
    next_btn = await page.query_selector(
        'a[rel="next"], .pagination-next, .next-page, [aria-label="次のページ"]'
    )
    return next_btn is not None


async def main():
    records = []
    seen_urls = set()

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=HEADLESS)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
        )
        page = await context.new_page()

        # Login
        await login(page)

        for keyword in SEARCH_KEYWORDS:
            print(f"\n[{keyword}] スクレイピング開始")
            job_urls = []

            for pg in range(1, MAX_PAGES + 1):
                url = SEARCH_URL.format(
                    keyword=keyword.replace(' ', '+'), page=pg
                )
                print(f"  一覧ページ {pg}: {url}")
                new_urls = await scrape_list_page(page, url)

                # 重複除去
                new_urls = [u for u in new_urls if u not in seen_urls]
                job_urls.extend(new_urls)
                seen_urls.update(new_urls)
                print(f"    → {len(new_urls)}件取得 (累計{len(job_urls)}件)")

                if not new_urls:
                    print("    → 新規URLなし、次のキーワードへ")
                    break
                has_next = await check_next_page_exists(page)
                if not has_next:
                    break

            # 詳細ページ取得
            for i, job_url in enumerate(job_urls, 1):
                print(f"  [{i}/{len(job_urls)}] {job_url}")
                data = await scrape_detail_page(page, job_url)
                if data:
                    data['_keyword'] = keyword
                    records.append(data)

                # 進捗保存（途中クラッシュ対策）
                if i % 20 == 0:
                    _save(records, f"_checkpoint_{OUTPUT_FILE}")

        await browser.close()

    # 最終保存
    _save(records, OUTPUT_FILE)
    print(f"\n✅ 完了: {len(records)}件 → {OUTPUT_FILE}")


def _save(records: list, path: str):
    if not records:
        return
    df = pd.DataFrame(records)
    df.to_excel(path, sheet_name='求人データ', index=False, engine='openpyxl')
    print(f"  💾 保存: {path} ({len(df)}件)")


if __name__ == "__main__":
    asyncio.run(main())
