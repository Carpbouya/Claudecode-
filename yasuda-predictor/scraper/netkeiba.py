"""netkeiba スクレイピング処理（I/O + オーケストレーション）。

パース処理は ``scraper.parsers``（純粋関数）に委譲する。本モジュールは
HTTP 取得・レート制限・キャッシュ・詳細ページの取得順序のみを担う。

規約配慮:
  - リクエスト間隔を最低 2〜3 秒空ける（``ScrapingConfig.min_interval_sec``）
  - 適切な User-Agent を設定
  - キャッシュで再取得を抑制（``HtmlCache`` + 実行内メモ）

ネットワーク不通・取得失敗時は ``ScrapeError`` を送出する。呼び出し側
（``get_race_data``）はサンプルデータへフォールバックして処理を継続する。
詳細ページ（馬/騎手/種牡馬/調教）の失敗は 1 件ずつ握って中立値で続行する。
"""
from __future__ import annotations

import logging
import re
import time

import requests

from config import SCRAPING, RaceProfile
from models import Horse, JockeyStats, RaceData, SireStats
from scraper import parsers
from scraper.cache import HtmlCache

log = logging.getLogger(__name__)

SHUTUBA_URL = "https://race.netkeiba.com/race/shutuba.html?race_id={race_id}"
ODDS_URL = "https://race.netkeiba.com/odds/index.html?race_id={race_id}"
TRAINING_URL = "https://race.netkeiba.com/race/oikiri.html?race_id={race_id}"
HORSE_URL = "https://db.netkeiba.com/horse/{horse_id}/"
JOCKEY_URL = "https://db.netkeiba.com/jockey/{jockey_id}/"
SIRE_URL = "https://db.netkeiba.com/horse/sire/{sire_id}/"

# 既知のレース ID（年 → race_id）。実運用では出馬表確定後に追記する。
# race_id 形式: 年(4) + 開催場(2) + 回(2) + 日(2) + R(2)
# 例: 安田記念2026 は確定後に "20260502xxxx" を設定（誤った推測値は置かない）。
KNOWN_RACE_IDS: dict[tuple[str, int], str] = {}


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
        # 実行内メモ（同一レースで重複する騎手/種牡馬の再取得を防ぐ）
        self._jockey_memo: dict[str, JockeyStats] = {}
        self._sire_memo: dict[str, SireStats] = {}

    # -- 低レベル取得 -------------------------------------------------------
    def _throttle(self) -> None:
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
        except requests.RequestException as exc:
            raise ScrapeError(f"取得失敗: {url} ({exc})") from exc
        resp.encoding = SCRAPING.encoding
        html = resp.text
        self.cache.set(url, html)
        return html

    # -- 高レベル -----------------------------------------------------------
    def fetch_race(self, race_id: str, profile: RaceProfile, *, enrich: bool = True) -> list[Horse]:
        """race_id から出走馬リスト（オッズ・詳細データ込み）を構築する。"""
        horses = parsers.parse_shutuba(self.fetch_html(SHUTUBA_URL.format(race_id=race_id)))
        if not horses:
            raise ScrapeError(f"出走馬を抽出できませんでした: race_id={race_id}")

        self._merge_odds(race_id, horses)
        self._merge_training(race_id, horses)

        if enrich:
            for h in horses:
                self._enrich_horse(h, profile)
        return horses

    # -- レース全体ページ ---------------------------------------------------
    def _merge_odds(self, race_id: str, horses: list[Horse]) -> None:
        try:
            odds = parsers.parse_odds(self.fetch_html(ODDS_URL.format(race_id=race_id)))
        except ScrapeError as exc:
            log.warning("オッズ取得をスキップ: %s", exc)
            return
        for h in horses:
            if h.number in odds:
                h.win_odds = odds[h.number]

    def _merge_training(self, race_id: str, horses: list[Horse]) -> None:
        try:
            training = parsers.parse_training(self.fetch_html(TRAINING_URL.format(race_id=race_id)))
        except ScrapeError as exc:
            log.warning("調教取得をスキップ: %s", exc)
            return
        for h in horses:
            if h.number in training:
                t, grade = training[h.number]
                h.training_time = t
                h.training_grade = grade

    # -- 馬個別の詳細取得 ---------------------------------------------------
    def _enrich_horse(self, h: Horse, profile: RaceProfile) -> None:
        # 馬ページ: 過去成績 + 血統
        if h.horse_id:
            try:
                html = self.fetch_html(HORSE_URL.format(horse_id=h.horse_id))
                h.past_results = parsers.parse_horse_results(html)
                h.sire, h.broodmare_sire, h.sire_id = parsers.parse_pedigree(html)
            except Exception as exc:  # ScrapeError 含む。1 件の失敗で全体を止めない
                log.warning("馬ページ取得をスキップ (%s): %s", h.name, exc)

        # 種牡馬ページ: コース/距離別成績
        if h.sire_id:
            try:
                h.sire_stats = self._sire_stats(h.sire_id, profile)
            except Exception as exc:  # ScrapeError 含む。1 件の失敗で全体を止めない
                log.warning("種牡馬ページ取得をスキップ (%s): %s", h.sire, exc)

        # 騎手ページ: コース別成績
        if h.jockey_id:
            try:
                h.jockey_stats = self._jockey_stats(h.jockey_id, profile)
            except Exception as exc:  # ScrapeError 含む。1 件の失敗で全体を止めない
                log.warning("騎手ページ取得をスキップ (%s): %s", h.jockey, exc)

    def _jockey_stats(self, jockey_id: str, profile: RaceProfile) -> JockeyStats:
        if jockey_id in self._jockey_memo:
            return self._jockey_memo[jockey_id]
        html = self.fetch_html(JOCKEY_URL.format(jockey_id=jockey_id))
        st = parsers.parse_jockey_course_stats(html, course=profile.course, surface=profile.surface)
        self._jockey_memo[jockey_id] = st
        return st

    def _sire_stats(self, sire_id: str, profile: RaceProfile) -> SireStats:
        if sire_id in self._sire_memo:
            return self._sire_memo[sire_id]
        html = self.fetch_html(SIRE_URL.format(sire_id=sire_id))
        st = parsers.parse_sire_course_stats(
            html, course=profile.course, surface=profile.surface,
            distance=profile.distance, distance_tolerance=profile.distance_tolerance,
        )
        self._sire_memo[sire_id] = st
        return st


# -- ヘルパ -----------------------------------------------------------------
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
    enrich: bool = True,
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
        horses = scraper.fetch_race(race_id, profile, enrich=enrich)
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
