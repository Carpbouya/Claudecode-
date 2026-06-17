import asyncio
import logging
import math
import time

import aiohttp

from config import PREFECTURES, HEADERS, DEFAULT_WORKERS
from worker import Worker
from storage import get_job_count

logger = logging.getLogger(__name__)


async def crawl_all(workers: int = DEFAULT_WORKERS,
                     delay_min: float = 1.5, delay_max: float = 3.0,
                     max_pages_per_pref: int = 500):
    semaphore = asyncio.Semaphore(workers)

    connector = aiohttp.TCPConnector(limit=workers + 2, force_close=False)
    async with aiohttp.ClientSession(
        headers=HEADERS, connector=connector
    ) as session:
        chunks = _split_prefectures(PREFECTURES, workers)
        worker_instances = []
        tasks = []

        for i, chunk in enumerate(chunks):
            w = Worker(i + 1, semaphore, session, delay_min, delay_max)
            worker_instances.append(w)
            tasks.append(
                _run_worker(w, chunk, max_pages_per_pref)
            )

        start = time.time()
        logger.info(f"クロール開始: {len(PREFECTURES)}都道府県 / {workers}ワーカー")
        logger.info(f"リクエスト間隔: {delay_min}-{delay_max}秒")

        results = await asyncio.gather(*tasks, return_exceptions=True)

        elapsed = time.time() - start
        total = sum(r for r in results if isinstance(r, int))
        db_total = get_job_count()

        logger.info("=" * 60)
        logger.info(f"クロール完了")
        logger.info(f"  取得件数: {total:,} 件")
        logger.info(f"  DB総数:   {db_total:,} 件")
        logger.info(f"  所要時間: {elapsed/60:.1f} 分")
        logger.info("=" * 60)

        for r in results:
            if isinstance(r, Exception):
                logger.error(f"ワーカーエラー: {r}")

    return total


async def _run_worker(worker: Worker, prefectures: list[str],
                       max_pages: int) -> int:
    total = 0
    for pref in prefectures:
        count = await worker.crawl_prefecture(pref, max_pages)
        total += count
    return total


def _split_prefectures(prefs: list[str], n: int) -> list[list[str]]:
    chunk_size = math.ceil(len(prefs) / n)
    return [prefs[i:i + chunk_size] for i in range(0, len(prefs), chunk_size)]
