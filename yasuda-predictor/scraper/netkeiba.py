"""netkeiba スクレイピング処理。

規約配慮:
  - リクエスト間隔を最低 2〜3 秒空ける（``ScrapingConfig.min_interval_sec``）
  - 適切な User-Agent を設定
  - キャッシュで再取得を抑制（``HtmlCache``）

ネットワーク不通・取得失敗時は ``ScrapeError`` を送出する。呼び出し側
（``get_race_data``）はサンプルデータへフォールバックして処理を継続する。
"""
from __future__ import annotations

import logging
import re
import time

import requests
from bs4 import BeautifulSoup

from config import SCRAPING, RaceProfile
from models import Horse, RaceData
from scraper.cache import HtmlCache

log = logging.getLogger(__name__)

SHUTUBA_URL = "https://race.netkeiba.com/race/shutuba.html?race_id={race_id}"
ODDS_URL = "https://race.netkeiba.com/odds/index.html?race_id={race_id}"

# 既知のレース ID（年 → race_id）。実運用では出馬表確定後に追記する。
# race_id 形式: 年(4) + 開催場(2) + 回(2) + 日(2) + R(2)
KNOWN_RACE_IDS: dict[tuple[str, int], str] = {
    # ("安田記念", 2026): "202605021011",  # 例: 東京2回5日11R（確定後に設定）
}


class ScrapeError(RuntimeError):
    """スクレイピング失敗を表す例外。"""


class NetkeibaScraper:
    """レート制限・キャッシュ付きの netkeiba クライアント。"""

    def __init__(self, use_cache: bool = True) -> None:
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": SCRAPING.user_agent})
        self.cache = HtmlCache(SCRAPING.cache_ttl_sec)
        self.use_cache = use_cache
        self._last_request_at = 0.0

    # -- 低レベル取得 -------------------------------------------------------
    def _throttle(self) -> None:
        """前回リクエストから最低間隔を空ける。"""
        elapsed = time.time() - self._last_request_at
        wait = SCRAPING.min_interval_sec - elapsed
        if wait > 0:
            time.sleep(wait)

    def fetch_html(self, url: str) -> str:
        if self.use_cache:
            cached = self.cache.get(url)
            if cached is not None:
                log.info("cache hit: %s", url)
                return cached
        self._throttle()
        try:
            resp = self.session.get(url, timeout=SCRAPING.timeout_sec)
            self._last_request_at = time.time()
            resp.raise_for_status()
        except requests.RequestException as exc:  # ネットワーク/HTTP エラー
            raise ScrapeError(f"取得失敗: {url} ({exc})") from exc
        resp.encoding = SCRAPING.encoding
        html = resp.text
        self.cache.set(url, html)
        return html

    # -- パース -------------------------------------------------------------
    @staticmethod
    def parse_shutuba(html: str) -> list[Horse]:
        """出馬表 HTML から馬番・枠番・馬名・騎手を抽出する。"""
        soup = BeautifulSoup(html, "html.parser")
        horses: list[Horse] = []
        rows = soup.select("table.Shutuba_Table tr.HorseList")
        for row in rows:
            try:
                frame = _to_int(_text(row.select_one("td[class^=Waku] span, td.Waku span")))
                number = _to_int(_text(row.select_one("td.Umaban, td[class^=Umaban]")))
                name = _text(row.select_one("span.HorseName a, td.HorseInfo a"))
                jockey = _text(row.select_one("td.Jockey a"))
                odds = _to_float(_text(row.select_one("td.Popular span, td.Txt_R span")))
                if not name:
                    continue
                horses.append(
                    Horse(
                        number=number or len(horses) + 1,
                        frame=frame or 0,
                        name=name,
                        jockey=jockey,
                        win_odds=odds or 0.0,
                    )
                )
            except Exception as exc:  # 1 行の失敗は握って続行（非機能要件）
                log.warning("行のパース失敗をスキップ: %s", exc)
                continue
        return horses

    @staticmethod
    def parse_odds(html: str) -> dict[int, float]:
        """単勝オッズ HTML から 馬番 → オッズ を抽出する。"""
        soup = BeautifulSoup(html, "html.parser")
        result: dict[int, float] = {}
        for row in soup.select("tr"):
            num = _to_int(_text(row.select_one("td.Umaban, td[class^=Umaban]")))
            odds = _to_float(_text(row.select_one("td.Odds span, span.Odds")))
            if num and odds:
                result[num] = odds
        return result

    # -- 高レベル -----------------------------------------------------------
    def fetch_race(self, race_id: str) -> list[Horse]:
        """race_id から出走馬リスト（オッズ込み）を構築する。"""
        horses = self.parse_shutuba(self.fetch_html(SHUTUBA_URL.format(race_id=race_id)))
        if not horses:
            raise ScrapeError(f"出走馬を抽出できませんでした: race_id={race_id}")
        # オッズページがあれば最新値で上書き
        try:
            odds = self.parse_odds(self.fetch_html(ODDS_URL.format(race_id=race_id)))
            for h in horses:
                if h.number in odds:
                    h.win_odds = odds[h.number]
        except ScrapeError as exc:
            log.warning("オッズ取得をスキップ: %s", exc)
        return horses


# -- ヘルパ -----------------------------------------------------------------
def _text(node) -> str:
    return node.get_text(strip=True) if node else ""


def _to_int(s: str) -> int | None:
    m = re.search(r"\d+", s or "")
    return int(m.group()) if m else None


def _to_float(s: str) -> float | None:
    m = re.search(r"\d+(?:\.\d+)?", (s or "").replace(",", ""))
    return float(m.group()) if m else None


def race_id_from_url(url: str) -> str:
    m = re.search(r"race_id=(\w+)", url)
    if not m:
        raise ScrapeError(f"URL から race_id を抽出できません: {url}")
    return m.group(1)


def get_race_data(
    profile: RaceProfile,
    year: int,
    *,
    url: str | None = None,
    use_cache: bool = True,
    use_sample: bool = False,
) -> RaceData:
    """レースデータを取得する高水準 API。

    取得に失敗した場合（ネットワーク不通・ID 未登録など）はサンプルデータに
    フォールバックし、``RaceData.source`` で出所を示す。
    """
    from scraper.sample_data import build_sample_race  # 遅延 import で循環回避

    if use_sample:
        log.info("サンプルデータを使用します（--sample 指定）")
        return build_sample_race(profile, year)

    race_id: str | None = None
    if url:
        race_id = race_id_from_url(url)
    else:
        race_id = KNOWN_RACE_IDS.get((profile.name, year))

    if not race_id:
        log.warning(
            "race_id が未登録のためサンプルデータにフォールバックします "
            "（--url で指定するか config.KNOWN_RACE_IDS に追加してください）"
        )
        return build_sample_race(profile, year)

    scraper = NetkeibaScraper(use_cache=use_cache)
    try:
        horses = scraper.fetch_race(race_id)
    except ScrapeError as exc:
        log.error("スクレイピング失敗のためサンプルにフォールバック: %s", exc)
        return build_sample_race(profile, year)

    return RaceData(
        race_id=race_id,
        name=profile.name,
        year=year,
        course=profile.course,
        surface=profile.surface,
        distance=profile.distance,
        horses=horses,
        source="scraper",
    )
