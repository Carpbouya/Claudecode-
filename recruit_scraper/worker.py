import asyncio
import random
import logging
from urllib.parse import urlencode

import aiohttp

from config import (
    SEARCH_URL, HEADERS, REQUEST_TIMEOUT,
    MAX_RETRIES, RETRY_BACKOFF,
    DEFAULT_DELAY_MIN, DEFAULT_DELAY_MAX,
)
from parser import parse_listing_page, parse_detail_page, get_total_count
from storage import bulk_insert_jobs, mark_page_done, is_page_done

logger = logging.getLogger(__name__)


class Worker:
    def __init__(self, worker_id: int, semaphore: asyncio.Semaphore,
                 session: aiohttp.ClientSession,
                 delay_min: float = DEFAULT_DELAY_MIN,
                 delay_max: float = DEFAULT_DELAY_MAX):
        self.worker_id = worker_id
        self.semaphore = semaphore
        self.session = session
        self.delay_min = delay_min
        self.delay_max = delay_max
        self.total_fetched = 0

    async def _fetch(self, url: str) -> str | None:
        for attempt in range(MAX_RETRIES):
            try:
                async with self.semaphore:
                    await asyncio.sleep(random.uniform(self.delay_min, self.delay_max))
                    async with self.session.get(
                        url, timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
                    ) as resp:
                        if resp.status == 200:
                            return await resp.text()
                        elif resp.status == 403:
                            logger.warning(
                                f"[W{self.worker_id}] 403 Forbidden: {url}"
                            )
                            await asyncio.sleep(RETRY_BACKOFF[attempt] * 2)
                        elif resp.status == 429:
                            wait = RETRY_BACKOFF[attempt] * 3
                            logger.warning(
                                f"[W{self.worker_id}] 429 Rate limited, waiting {wait}s"
                            )
                            await asyncio.sleep(wait)
                        else:
                            logger.warning(
                                f"[W{self.worker_id}] HTTP {resp.status}: {url}"
                            )
                            await asyncio.sleep(RETRY_BACKOFF[attempt])
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                logger.warning(
                    f"[W{self.worker_id}] Attempt {attempt+1} failed: {e}"
                )
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_BACKOFF[attempt])
        logger.error(f"[W{self.worker_id}] 全リトライ失敗: {url}")
        return None

    async def crawl_prefecture(self, prefecture: str,
                                 max_pages: int = 500) -> int:
        logger.info(f"[W{self.worker_id}] {prefecture} 開始")
        params = {"area": prefecture}
        url = f"{SEARCH_URL}?{urlencode(params)}"
        total_jobs = 0

        for page in range(1, max_pages + 1):
            if is_page_done(prefecture, page):
                logger.debug(f"[W{self.worker_id}] {prefecture} p{page} スキップ(済)")
                continue

            html = await self._fetch(url)
            if not html:
                logger.warning(f"[W{self.worker_id}] {prefecture} p{page} 取得失敗、中断")
                break

            jobs, next_url = parse_listing_page(html, url, prefecture)

            if not jobs:
                logger.info(f"[W{self.worker_id}] {prefecture} p{page} 求人0件、完了")
                break

            bulk_insert_jobs(jobs)
            mark_page_done(prefecture, page)
            total_jobs += len(jobs)
            self.total_fetched += len(jobs)

            logger.info(
                f"[W{self.worker_id}] {prefecture} p{page}: "
                f"{len(jobs)}件 (県計{total_jobs} / 全体{self.total_fetched})"
            )

            if not next_url:
                logger.info(f"[W{self.worker_id}] {prefecture} 最終ページ到達")
                break
            url = next_url

        logger.info(f"[W{self.worker_id}] {prefecture} 完了: {total_jobs}件")
        return total_jobs

    async def fetch_details(self, jobs: list[dict]) -> list[dict]:
        results = []
        for i, job in enumerate(jobs):
            url = job.get("source_url")
            if not url:
                continue
            html = await self._fetch(url)
            if not html:
                continue
            detail = parse_detail_page(html)
            detail["job_id"] = job["id"]
            results.append(detail)

            if (i + 1) % 20 == 0:
                logger.info(
                    f"[W{self.worker_id}] 詳細取得中: {i+1}/{len(jobs)}"
                )
        return results
