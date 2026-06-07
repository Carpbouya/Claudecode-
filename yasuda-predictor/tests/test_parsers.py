"""パーサー単体テスト（フィクスチャ駆動・ネット不要）。"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scraper import parsers  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def load(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


class TestShutuba(unittest.TestCase):
    def setUp(self):
        self.horses = parsers.parse_shutuba(load("shutuba.html"))

    def test_count_and_fields(self):
        self.assertEqual(len(self.horses), 2)
        h = self.horses[0]
        self.assertEqual(h.number, 7)
        self.assertEqual(h.frame, 4)
        self.assertEqual(h.name, "サンプルウイナー")
        self.assertEqual(h.jockey, "ルメール")
        self.assertAlmostEqual(h.win_odds, 3.2)

    def test_ids_extracted(self):
        h = self.horses[0]
        self.assertEqual(h.horse_id, "2019105212")
        self.assertEqual(h.jockey_id, "05339")
        self.assertEqual(self.horses[1].horse_id, "2020104999")
        self.assertEqual(self.horses[1].jockey_id, "01088")


class TestOdds(unittest.TestCase):
    def test_parse_odds(self):
        odds = parsers.parse_odds(load("odds.html"))
        self.assertEqual(odds, {7: 3.0, 3: 6.1})


class TestHorseResults(unittest.TestCase):
    def setUp(self):
        self.results = parsers.parse_horse_results(load("horse_page.html"))

    def test_count(self):
        self.assertEqual(len(self.results), 3)

    def test_surface_distance_split(self):
        r = self.results[0]
        self.assertEqual(r.surface, "芝")
        self.assertEqual(r.distance, 1600)
        self.assertEqual(self.results[2].surface, "ダート")
        self.assertEqual(self.results[2].distance, 1800)

    def test_finish_size_pop_venue(self):
        r = self.results[0]
        self.assertEqual(r.finish, 1)
        self.assertEqual(r.field_size, 16)
        self.assertEqual(r.popularity, 1)
        self.assertEqual(r.course, "東京")
        self.assertEqual(self.results[2].course, "中山")

    def test_limit(self):
        limited = parsers.parse_horse_results(load("horse_page.html"), limit=2)
        self.assertEqual(len(limited), 2)


class TestPedigree(unittest.TestCase):
    def test_pedigree(self):
        sire, bms, sire_id = parsers.parse_pedigree(load("horse_page.html"))
        self.assertEqual(sire, "ディープインパクト")
        self.assertEqual(sire_id, "2005103504")
        self.assertEqual(bms, "キングカメハメハ")


class TestJockeyStats(unittest.TestCase):
    def test_tokyo_row(self):
        st = parsers.parse_jockey_course_stats(load("jockey_page.html"), course="東京")
        self.assertEqual(st.starts, 120)   # 34+22+16+48
        self.assertEqual(st.wins, 34)
        self.assertEqual(st.shows, 72)     # 34+22+16

    def test_missing_course(self):
        st = parsers.parse_jockey_course_stats(load("jockey_page.html"), course="札幌")
        self.assertEqual(st.starts, 0)


class TestSireStats(unittest.TestCase):
    def test_distance_window(self):
        # 東京芝 1600±200 → 1400 + 1600 + 1800 を合算
        st = parsers.parse_sire_course_stats(
            load("sire_page.html"), course="東京", surface="芝",
            distance=1600, distance_tolerance=200,
        )
        self.assertEqual(st.runs, 239)   # 65+132+42
        self.assertEqual(st.wins, 40)    # 10+25+5
        self.assertEqual(st.shows, 89)   # 25+52+12

    def test_excludes_other_course_and_surface(self):
        st = parsers.parse_sire_course_stats(
            load("sire_page.html"), course="中山", surface="芝",
            distance=1600, distance_tolerance=0,
        )
        self.assertEqual(st.runs, 54)    # 中山芝1600 のみ 8+6+5+35


class TestTraining(unittest.TestCase):
    def test_parse(self):
        t = parsers.parse_training(load("oikiri.html"))
        self.assertEqual(set(t), {7, 3, 14})
        self.assertAlmostEqual(t[7][0], 49.8)
        self.assertEqual(t[7][1], "A")
        self.assertEqual(t[3][1], "A")   # S → A
        self.assertEqual(t[14][1], "B")


class TestErrorTolerance(unittest.TestCase):
    """壊れた/空の HTML でも例外を投げず中立値を返す。"""

    def test_empty_horse_page(self):
        self.assertEqual(parsers.parse_horse_results(load("horse_page_empty.html")), [])
        self.assertEqual(parsers.parse_pedigree(load("horse_page_empty.html")), ("", "", ""))

    def test_garbage(self):
        self.assertEqual(parsers.parse_shutuba("<html></html>"), [])
        self.assertEqual(parsers.parse_odds(""), {})
        self.assertEqual(parsers.parse_training("not html"), {})
        self.assertEqual(parsers.parse_jockey_course_stats("", course="東京").starts, 0)


if __name__ == "__main__":
    unittest.main()
