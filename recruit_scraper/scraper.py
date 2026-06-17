"""
リクルートエージェント求人スクレイパー

クライアント企業からの採用依頼時に、市場・競合の求人票を収集・分析するためのツール。
全国の求人情報を取得し、SQLiteに保存する。
"""

import re
import time
import random
import logging
import argparse
from urllib.parse import urljoin, urlencode

import requests
from bs4 import BeautifulSoup

from config import (
    BASE_URL,
    SEARCH_URL,
    HEADERS,
    REQUEST_DELAY,
    MAX_PAGES,
    REQUEST_TIMEOUT,
    PREFECTURES,
    JOB_CATEGORIES,
)
from models import init_db, bulk_upsert_jobs

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class RecruitAgentScraper:
    def __init__(self, delay=REQUEST_DELAY, max_pages=MAX_PAGES):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.delay = delay
        self.max_pages = max_pages
        self.scraped_count = 0

    def _wait(self):
        wait_time = random.uniform(*self.delay)
        time.sleep(wait_time)

    def _get_page(self, url: str) -> BeautifulSoup | None:
        try:
            self._wait()
            response = self.session.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            response.encoding = response.apparent_encoding
            return BeautifulSoup(response.text, "lxml")
        except requests.RequestException as e:
            logger.error(f"ページ取得失敗: {url} - {e}")
            return None

    def _parse_salary(self, salary_text: str) -> tuple[int | None, int | None]:
        if not salary_text:
            return None, None
        numbers = re.findall(r"(\d+)", salary_text.replace(",", ""))
        if len(numbers) >= 2:
            return int(numbers[0]) * 10000, int(numbers[1]) * 10000
        elif len(numbers) == 1:
            val = int(numbers[0]) * 10000
            return val, val
        return None, None

    def _parse_job_listing(self, card, search_url: str) -> dict | None:
        try:
            title_elem = card.select_one(
                "h2 a, h3 a, .job-title a, .jobTitle a, "
                "[class*='title'] a, [class*='Title'] a"
            )
            if not title_elem:
                title_elem = card.select_one("h2, h3, .job-title, .jobTitle")

            title = title_elem.get_text(strip=True) if title_elem else None
            if not title:
                return None

            link = None
            if title_elem and title_elem.name == "a":
                link = title_elem.get("href", "")
            elif title_elem:
                link_elem = title_elem.find("a")
                if link_elem:
                    link = link_elem.get("href", "")

            if link and not link.startswith("http"):
                link = urljoin(BASE_URL, link)

            company_elem = card.select_one(
                ".company-name, .companyName, [class*='company'], "
                "[class*='Company'], .corp-name"
            )
            company = company_elem.get_text(strip=True) if company_elem else ""

            salary_elem = card.select_one(
                ".salary, .income, [class*='salary'], [class*='Salary'], "
                "[class*='income'], [class*='年収']"
            )
            salary_text = salary_elem.get_text(strip=True) if salary_elem else ""
            salary_min, salary_max = self._parse_salary(salary_text)

            location_elem = card.select_one(
                ".location, .area, [class*='location'], [class*='Location'], "
                "[class*='area'], [class*='勤務地']"
            )
            location = location_elem.get_text(strip=True) if location_elem else ""

            prefecture = self._detect_prefecture(location)

            desc_elem = card.select_one(
                ".description, .job-desc, [class*='description'], "
                "[class*='Description'], [class*='detail'], .summary"
            )
            description = desc_elem.get_text(strip=True) if desc_elem else ""

            category_elem = card.select_one(
                ".category, .job-type, [class*='category'], "
                "[class*='Category'], [class*='職種']"
            )
            job_category = category_elem.get_text(strip=True) if category_elem else ""

            return {
                "source_url": link or search_url,
                "title": title,
                "company_name": company,
                "industry": "",
                "job_category": job_category,
                "salary_min": salary_min,
                "salary_max": salary_max,
                "salary_text": salary_text,
                "location": location,
                "prefecture": prefecture,
                "work_style": "",
                "required_skills": "",
                "preferred_skills": "",
                "experience_years": "",
                "employment_type": "",
                "description": description,
                "benefits": "",
            }
        except Exception as e:
            logger.warning(f"求人カード解析エラー: {e}")
            return None

    def _parse_job_detail(self, url: str) -> dict:
        soup = self._get_page(url)
        if not soup:
            return {}

        detail = {}

        sections = soup.select("table tr, dl, .detail-section, .job-detail-section")
        for section in sections:
            header = section.select_one("th, dt, .label, .item-label")
            value = section.select_one("td, dd, .value, .item-value")
            if not header or not value:
                continue

            header_text = header.get_text(strip=True)
            value_text = value.get_text(strip=True)

            if "業種" in header_text or "業界" in header_text:
                detail["industry"] = value_text
            elif "必須" in header_text or "応募資格" in header_text:
                detail["required_skills"] = value_text
            elif "歓迎" in header_text or "あれば" in header_text:
                detail["preferred_skills"] = value_text
            elif "経験" in header_text and "年" in value_text:
                detail["experience_years"] = value_text
            elif "雇用形態" in header_text:
                detail["employment_type"] = value_text
            elif "勤務地" in header_text:
                detail["location"] = value_text
                detail["prefecture"] = self._detect_prefecture(value_text)
            elif "年収" in header_text or "給与" in header_text:
                detail["salary_text"] = value_text
                s_min, s_max = self._parse_salary(value_text)
                if s_min:
                    detail["salary_min"] = s_min
                if s_max:
                    detail["salary_max"] = s_max
            elif "福利" in header_text or "待遇" in header_text:
                detail["benefits"] = value_text
            elif "リモート" in header_text or "在宅" in header_text or "テレワーク" in header_text:
                detail["work_style"] = value_text
            elif "仕事内容" in header_text or "業務内容" in header_text:
                detail["description"] = value_text

        return detail

    def _detect_prefecture(self, text: str) -> str:
        if not text:
            return ""
        for pref in PREFECTURES:
            if pref in text:
                return pref
        return ""

    def _find_next_page(self, soup: BeautifulSoup) -> str | None:
        next_link = soup.select_one(
            "a.next, a[rel='next'], .pagination .next a, "
            ".pager .next a, [class*='next'] a, a:contains('次')"
        )
        if next_link:
            href = next_link.get("href", "")
            if href:
                return urljoin(BASE_URL, href) if not href.startswith("http") else href

        page_links = soup.select(".pagination a, .pager a, [class*='page'] a")
        for link in page_links:
            if "次" in link.get_text() or ">" in link.get_text():
                href = link.get("href", "")
                if href:
                    return urljoin(BASE_URL, href) if not href.startswith("http") else href
        return None

    def scrape_search_results(self, keyword: str = "",
                               prefecture: str = "",
                               category: str = "",
                               fetch_details: bool = False,
                               max_pages: int | None = None) -> list[dict]:
        pages = max_pages or self.max_pages
        all_jobs = []

        params = {}
        if keyword:
            params["keyword"] = keyword
        if prefecture and prefecture in PREFECTURES:
            params["area"] = PREFECTURES[prefecture]
        if category and category in JOB_CATEGORIES:
            params["jobtype"] = JOB_CATEGORIES[category]

        url = f"{SEARCH_URL}?{urlencode(params)}" if params else SEARCH_URL

        for page_num in range(1, pages + 1):
            logger.info(f"ページ {page_num} をスクレイピング中: {url}")
            soup = self._get_page(url)
            if not soup:
                logger.warning(f"ページ {page_num} の取得に失敗。中断します。")
                break

            job_cards = soup.select(
                ".job-card, .search-result-item, .job-list-item, "
                "[class*='jobCard'], [class*='JobCard'], "
                "[class*='result-item'], article.job, "
                ".cassetteRecruit, .cassetteRecruit__content"
            )

            if not job_cards:
                job_cards = soup.select("article, .card, [class*='item']")

            if not job_cards:
                logger.info(f"ページ {page_num} に求人カードが見つかりません。終了します。")
                break

            page_jobs = []
            for card in job_cards:
                job = self._parse_job_listing(card, url)
                if job:
                    if fetch_details and job.get("source_url"):
                        detail = self._parse_job_detail(job["source_url"])
                        job.update({k: v for k, v in detail.items() if v})
                    page_jobs.append(job)

            all_jobs.extend(page_jobs)
            self.scraped_count += len(page_jobs)
            logger.info(f"ページ {page_num}: {len(page_jobs)} 件取得 (累計: {self.scraped_count} 件)")

            next_url = self._find_next_page(soup)
            if not next_url:
                logger.info("次のページが見つかりません。完了です。")
                break
            url = next_url

        return all_jobs

    def scrape_all_prefectures(self, keyword: str = "",
                                category: str = "",
                                pages_per_pref: int = 5,
                                fetch_details: bool = False) -> list[dict]:
        all_jobs = []
        for pref_name in PREFECTURES:
            logger.info(f"=== {pref_name} のスクレイピング開始 ===")
            jobs = self.scrape_search_results(
                keyword=keyword,
                prefecture=pref_name,
                category=category,
                fetch_details=fetch_details,
                max_pages=pages_per_pref,
            )
            if jobs:
                bulk_upsert_jobs(jobs)
                all_jobs.extend(jobs)
            logger.info(f"=== {pref_name}: {len(jobs)} 件完了 ===")
        return all_jobs


def main():
    parser = argparse.ArgumentParser(description="リクルートエージェント求人スクレイパー")
    parser.add_argument("--keyword", "-k", default="", help="検索キーワード")
    parser.add_argument("--prefecture", "-p", default="", help="都道府県（例: 東京都）")
    parser.add_argument("--category", "-c", default="", help="職種カテゴリ")
    parser.add_argument("--all-prefectures", "-a", action="store_true",
                        help="全都道府県をスクレイピング")
    parser.add_argument("--pages", type=int, default=5, help="最大ページ数")
    parser.add_argument("--details", action="store_true", help="詳細ページも取得する")
    args = parser.parse_args()

    init_db()
    scraper = RecruitAgentScraper()

    if args.all_prefectures:
        jobs = scraper.scrape_all_prefectures(
            keyword=args.keyword,
            category=args.category,
            pages_per_pref=args.pages,
            fetch_details=args.details,
        )
    else:
        jobs = scraper.scrape_search_results(
            keyword=args.keyword,
            prefecture=args.prefecture,
            category=args.category,
            fetch_details=args.details,
            max_pages=args.pages,
        )
        if jobs:
            bulk_upsert_jobs(jobs)

    logger.info(f"スクレイピング完了。合計 {len(jobs)} 件の求人を取得しました。")


if __name__ == "__main__":
    main()
