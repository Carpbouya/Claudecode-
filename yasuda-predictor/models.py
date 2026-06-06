"""ドメインモデル。スクレイピング・スコアリング・買い目生成で共通利用する。"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PastResult:
    """1 走分の過去成績。"""

    date: str
    course: str          # 例: 東京
    surface: str         # 例: 芝
    distance: int        # m
    finish: int          # 着順（1 が 1 着）
    field_size: int      # 出走頭数
    popularity: int = 0  # 人気

    @property
    def is_win(self) -> bool:
        return self.finish == 1

    @property
    def is_quinella(self) -> bool:  # 連対（2 着以内）
        return self.finish <= 2

    @property
    def is_show(self) -> bool:  # 複勝圏（3 着以内）
        return self.finish <= 3


@dataclass
class JockeyStats:
    """騎手の当該コース成績。"""

    starts: int = 0
    wins: int = 0
    shows: int = 0  # 複勝（3 着以内）回数

    @property
    def win_rate(self) -> float:
        return self.wins / self.starts if self.starts else 0.0

    @property
    def show_rate(self) -> float:
        return self.shows / self.starts if self.starts else 0.0


@dataclass
class SireStats:
    """種牡馬（父）の当該コース・距離産駒成績。"""

    runs: int = 0
    wins: int = 0
    shows: int = 0

    @property
    def win_rate(self) -> float:
        return self.wins / self.runs if self.runs else 0.0

    @property
    def show_rate(self) -> float:
        return self.shows / self.runs if self.runs else 0.0


@dataclass
class Horse:
    """1 頭分の出走馬データ + 算出スコア。"""

    number: int            # 馬番
    frame: int             # 枠番
    name: str
    jockey: str
    win_odds: float        # 単勝オッズ
    place_odds: tuple[float, float] | None = None  # 複勝オッズ (下限, 上限)

    sire: str = ""              # 父
    broodmare_sire: str = ""    # 母父
    past_results: list[PastResult] = field(default_factory=list)
    jockey_stats: JockeyStats = field(default_factory=JockeyStats)
    sire_stats: SireStats = field(default_factory=SireStats)

    training_time: float | None = None  # 調教タイム（秒, 小さいほど速い）
    training_grade: str = "C"           # 調教評価 A/B/C

    # --- 算出結果（engine が埋める）---
    scores: dict[str, float] = field(default_factory=dict)  # 要素別スコア 0-100
    total_score: float = 0.0
    estimated_win_prob: float = 0.0  # 推定勝率 0-1
    expected_value: float = 0.0      # 期待値 = 単勝オッズ × 推定勝率
    mark: str = ""                   # ◎ ○ ▲ △ 等


@dataclass
class RaceData:
    """1 レース分のスクレイピング結果。"""

    race_id: str
    name: str
    year: int
    course: str
    surface: str
    distance: int
    horses: list[Horse] = field(default_factory=list)
    source: str = "scraper"  # "scraper" / "sample" / "cache"
