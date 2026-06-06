"""オフライン検証・デモ用のサンプルレースデータ。

ネットワーク不通時やデモ実行時に、スコアリング〜買い目〜レポートの
パイプライン全体を動かすためのフィクスチャ。馬名等は架空。
"""
from __future__ import annotations

from config import RaceProfile
from models import Horse, JockeyStats, PastResult, RaceData, SireStats


def _pr(date, finish, size, pop, course="東京", surface="芝", distance=1600):
    return PastResult(date, course, surface, distance, finish, size, pop)


def build_sample_race(profile: RaceProfile, year: int) -> RaceData:
    """プロファイルに沿ったサンプル出走馬を生成する。"""
    d = profile.distance
    horses = [
        Horse(
            number=7, frame=4, name="サンプルウイナー", jockey="ルメール",
            win_odds=3.2, place_odds=(1.3, 1.6),
            sire="ディープインパクト", broodmare_sire="キングカメハメハ",
            past_results=[
                _pr("2026-04", 1, 16, 1, distance=d), _pr("2026-02", 2, 18, 2, distance=d),
                _pr("2025-11", 1, 14, 1, distance=d), _pr("2025-06", 1, 16, 3, distance=d),
                _pr("2025-04", 3, 15, 2, distance=d),
            ],
            jockey_stats=JockeyStats(starts=120, wins=34, shows=72),
            sire_stats=SireStats(runs=410, wins=78, shows=205),
            training_time=49.8, training_grade="A",
        ),
        Horse(
            number=3, frame=2, name="サンプルチャレンジャー", jockey="川田",
            win_odds=5.6, place_odds=(1.7, 2.3),
            sire="ロードカナロア", broodmare_sire="ダイワメジャー",
            past_results=[
                _pr("2026-04", 2, 16, 3, distance=d), _pr("2026-03", 1, 12, 1, distance=d-200),
                _pr("2025-12", 4, 18, 5, distance=d), _pr("2025-09", 2, 14, 2, distance=d),
            ],
            jockey_stats=JockeyStats(starts=110, wins=26, shows=58),
            sire_stats=SireStats(runs=380, wins=70, shows=180),
            training_time=50.3, training_grade="A",
        ),
        Horse(
            number=12, frame=6, name="サンプルダークホース", jockey="津村",
            win_odds=15.0, place_odds=(3.2, 5.1),
            sire="ハーツクライ", broodmare_sire="サンデーサイレンス",
            past_results=[
                _pr("2026-05", 3, 16, 7, distance=d), _pr("2026-02", 5, 18, 9, distance=d),
                _pr("2025-10", 2, 13, 6, distance=d), _pr("2025-05", 1, 12, 4, distance=d),
            ],
            jockey_stats=JockeyStats(starts=90, wins=12, shows=30),
            sire_stats=SireStats(runs=300, wins=42, shows=120),
            training_time=49.5, training_grade="A",
        ),
        Horse(
            number=14, frame=7, name="サンプルベテラン", jockey="横山武",
            win_odds=8.1, place_odds=(2.1, 3.0),
            sire="エピファネイア", broodmare_sire="キングカメハメハ",
            past_results=[
                _pr("2026-04", 4, 16, 4, distance=d), _pr("2026-01", 3, 16, 5, distance=d),
                _pr("2025-11", 6, 18, 8, distance=d),
            ],
            jockey_stats=JockeyStats(starts=100, wins=18, shows=45),
            sire_stats=SireStats(runs=350, wins=55, shows=150),
            training_time=50.8, training_grade="B",
        ),
        Horse(
            number=1, frame=1, name="サンプルスプリンター", jockey="武豊",
            win_odds=11.0, place_odds=(2.8, 4.2),
            sire="ロードカナロア", broodmare_sire="フジキセキ",
            past_results=[
                _pr("2026-03", 1, 16, 2, distance=d-200), _pr("2025-12", 2, 16, 3, distance=d-200),
                _pr("2025-10", 7, 18, 5, distance=d),
            ],
            jockey_stats=JockeyStats(starts=105, wins=20, shows=50),
            sire_stats=SireStats(runs=380, wins=70, shows=180),
            training_time=50.5, training_grade="B",
        ),
        Horse(
            number=9, frame=5, name="サンプルルーキー", jockey="戸崎",
            win_odds=22.0, place_odds=(4.5, 7.0),
            sire="キズナ", broodmare_sire="クロフネ",
            past_results=[
                _pr("2026-04", 5, 16, 8, distance=d), _pr("2026-02", 8, 18, 12, distance=d),
                _pr("2025-11", 4, 14, 6, distance=d),
            ],
            jockey_stats=JockeyStats(starts=95, wins=14, shows=38),
            sire_stats=SireStats(runs=260, wins=32, shows=95),
            training_time=51.2, training_grade="C",
        ),
        Horse(
            number=5, frame=3, name="サンプルグレイ", jockey="松山",
            win_odds=18.0, place_odds=(3.8, 6.0),
            sire="モーリス", broodmare_sire="ディープインパクト",
            past_results=[
                _pr("2026-03", 6, 16, 9, distance=d), _pr("2025-12", 3, 16, 7, distance=d),
                _pr("2025-09", 9, 18, 11, distance=d),
            ],
            jockey_stats=JockeyStats(starts=88, wins=11, shows=29),
            sire_stats=SireStats(runs=240, wins=30, shows=88),
            training_time=51.0, training_grade="B",
        ),
        Horse(
            number=16, frame=8, name="サンプルアウトサイダー", jockey="田辺",
            win_odds=45.0, place_odds=(8.0, 14.0),
            sire="ドゥラメンテ", broodmare_sire="シンボリクリスエス",
            past_results=[
                _pr("2026-04", 10, 16, 14, distance=d), _pr("2026-01", 12, 16, 15, distance=d),
            ],
            jockey_stats=JockeyStats(starts=80, wins=8, shows=22),
            sire_stats=SireStats(runs=210, wins=24, shows=70),
            training_time=51.8, training_grade="C",
        ),
    ]
    return RaceData(
        race_id=f"SAMPLE-{year}",
        name=profile.name,
        year=year,
        course=profile.course,
        surface=profile.surface,
        distance=profile.distance,
        horses=horses,
        source="sample",
    )
