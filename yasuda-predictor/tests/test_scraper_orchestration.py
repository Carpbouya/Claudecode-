"""fetch_race のオーケストレーション検証（fetch_html をスタブ化・ネット不要）。"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import get_profile  # noqa: E402
from scraper import netkeiba  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def load(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def make_stub(raise_on: str | None = None):
    """URL パターンに応じて適切なフィクスチャを返す fetch_html スタブ。"""
    def fetch_html(url: str) -> str:
        if raise_on and raise_on in url:
            raise netkeiba.ScrapeError(f"stub error for {url}")
        if "shutuba" in url:
            return load("shutuba.html")
        if "odds" in url:
            return load("odds.html")
        if "oikiri" in url:
            return load("oikiri.html")
        if "/jockey/" in url:
            return load("jockey_page.html")
        if "/horse/sire/" in url:
            return load("sire_page.html")
        if "/horse/" in url:
            return load("horse_page.html")
        return "<html></html>"
    return fetch_html


class TestOrchestration(unittest.TestCase):
    def setUp(self):
        self.profile = get_profile("安田記念")
        self.scraper = netkeiba.NetkeibaScraper(use_cache=False)

    def test_full_enrichment(self):
        self.scraper.fetch_html = make_stub()
        horses = self.scraper.fetch_race("TEST", self.profile, enrich=True)

        self.assertEqual(len(horses), 2)
        h = horses[0]
        # 出馬表 + ID
        self.assertEqual(h.number, 7)
        self.assertEqual(h.horse_id, "2019105212")
        # オッズページで上書き（odds.html の 3.0）
        self.assertAlmostEqual(h.win_odds, 3.0)
        # 調教ページ merge
        self.assertAlmostEqual(h.training_time, 49.8)
        self.assertEqual(h.training_grade, "A")
        # 馬ページ: 過去成績 + 血統
        self.assertEqual(len(h.past_results), 3)
        self.assertEqual(h.sire, "ディープインパクト")
        self.assertEqual(h.broodmare_sire, "キングカメハメハ")
        # 種牡馬ページ
        self.assertEqual(h.sire_stats.runs, 239)
        # 騎手ページ
        self.assertEqual(h.jockey_stats.starts, 120)

    def test_no_enrich(self):
        self.scraper.fetch_html = make_stub()
        horses = self.scraper.fetch_race("TEST", self.profile, enrich=False)
        # 出馬表/オッズ/調教は入るが、馬個別の詳細は空のまま
        self.assertEqual(horses[0].past_results, [])
        self.assertEqual(horses[0].sire, "")
        self.assertEqual(horses[0].jockey_stats.starts, 0)

    def test_per_horse_error_tolerance(self):
        # 馬ページ取得が常に失敗しても、レース自体は返り他要素は埋まる
        self.scraper.fetch_html = make_stub(raise_on="/horse/")
        horses = self.scraper.fetch_race("TEST", self.profile, enrich=True)
        self.assertEqual(len(horses), 2)
        self.assertEqual(horses[0].past_results, [])   # 失敗→デフォルト
        self.assertEqual(horses[0].sire, "")
        # 騎手ページは別 URL なので成功している
        self.assertEqual(horses[0].jockey_stats.starts, 120)

    def test_shutuba_failure_raises(self):
        self.scraper.fetch_html = make_stub(raise_on="shutuba")
        with self.assertRaises(netkeiba.ScrapeError):
            self.scraper.fetch_race("TEST", self.profile)


if __name__ == "__main__":
    unittest.main()
