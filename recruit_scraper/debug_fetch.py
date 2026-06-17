"""1ページだけ取得してHTMLをダンプする。パーサー調整用。"""
import asyncio
import aiohttp
from config import SEARCH_BASE, HEADERS

async def main():
    url = f"{SEARCH_BASE}area-hokkaido/"
    print(f"Fetching: {url}")
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            print(f"HTTP {resp.status}")
            print(f"Final URL: {resp.url}")
            html = await resp.text()
            print(f"HTML length: {len(html)}")

            with open("debug_page.html", "w", encoding="utf-8") as f:
                f.write(html)
            print("Saved to debug_page.html")

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "lxml")

            # タイトルタグ
            title = soup.find("title")
            print(f"\nPage title: {title.get_text() if title else 'N/A'}")

            # 件数を探す
            import re
            text = soup.get_text()
            counts = re.findall(r'([\d,]+)\s*件', text)
            if counts:
                print(f"件数候補: {counts}")

            # 求人カードっぽい要素を探す
            print("\n=== 候補セレクタ ===")
            for selector in [
                "article", ".cassetteRecruit", "[class*='job']",
                "[class*='Job']", "[class*='card']", "[class*='Card']",
                "[class*='item']", "[class*='Item']",
                "[class*='result']", "[class*='Result']",
                "[class*='recruit']", "[class*='Recruit']",
                "[class*='list'] > *",
            ]:
                found = soup.select(selector)
                if found:
                    print(f"  {selector}: {len(found)} 個")
                    first = found[0]
                    classes = first.get("class", [])
                    tag = first.name
                    print(f"    最初の要素: <{tag} class='{' '.join(classes)}'>")
                    # 中のテキスト先頭
                    inner = first.get_text(strip=True)[:150]
                    print(f"    テキスト: {inner}")

            # aタグでhrefに/job_search/が含まれるリンクを探す
            print("\n=== 求人リンク候補 ===")
            job_links = soup.select("a[href*='/job_search/']")
            seen = set()
            for a in job_links[:10]:
                href = a.get("href", "")
                if href not in seen:
                    seen.add(href)
                    print(f"  {href}  -> {a.get_text(strip=True)[:60]}")

asyncio.run(main())
