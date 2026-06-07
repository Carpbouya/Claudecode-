"""設定値の一元管理。

重み・レースプロファイル・スクレイピング設定を dataclass で定義する。
GI 展開時は ``RACE_PROFILES`` にエントリを追加するだけで対応できる構造。
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ScoreWeights:
    """総合スコアの重み（合計 1.0 になるようにする）。"""

    past_results: float = 0.30  # 過去成績
    jockey: float = 0.20        # 騎手
    training: float = 0.20      # 調教
    bloodline: float = 0.15     # 血統
    odds_value: float = 0.15    # 期待値（穴要素）

    def as_dict(self) -> dict[str, float]:
        return {
            "past_results": self.past_results,
            "jockey": self.jockey,
            "training": self.training,
            "bloodline": self.bloodline,
            "odds_value": self.odds_value,
        }

    def total(self) -> float:
        return sum(self.as_dict().values())


@dataclass(frozen=True)
class RaceProfile:
    """レース特性。スコアリングはこのプロファイルを共通利用する。"""

    name: str
    distance: int   # m
    course: str     # 例: 東京
    surface: str    # 例: 芝
    weights: ScoreWeights = field(default_factory=ScoreWeights)
    # 距離許容幅（±この範囲を「同条件」とみなして過去成績/血統を評価）
    distance_tolerance: int = 200


# --- GI レースプロファイル -------------------------------------------------
# 重みはレース特性に合わせて変更するだけ。ロジック本体は共通利用される。
RACE_PROFILES: dict[str, RaceProfile] = {
    "安田記念": RaceProfile(
        name="安田記念",
        distance=1600,
        course="東京",
        surface="芝",
        weights=ScoreWeights(0.30, 0.20, 0.20, 0.15, 0.15),
    ),
    "ダービー": RaceProfile(
        name="ダービー",
        distance=2400,
        course="東京",
        surface="芝",
        # 距離が長いほど展開・スタミナ寄り → 過去成績重視・期待値やや控えめ
        weights=ScoreWeights(0.35, 0.20, 0.20, 0.15, 0.10),
    ),
    "有馬記念": RaceProfile(
        name="有馬記念",
        distance=2500,
        course="中山",
        surface="芝",
        weights=ScoreWeights(0.35, 0.15, 0.20, 0.15, 0.15),
    ),
}


@dataclass(frozen=True)
class ScrapingConfig:
    """スクレイピングの行儀（規約配慮）設定。"""

    # リクエスト間隔（秒）。過剰アクセス防止のため最低 2〜3 秒。
    min_interval_sec: float = 2.5
    user_agent: str = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36 yasuda-predictor/1.0"
    )
    timeout_sec: int = 15
    # キャッシュ有効期限（秒）。デフォルト 6 時間。
    cache_ttl_sec: int = 6 * 60 * 60
    encoding: str = "EUC-JP"  # netkeiba は EUC-JP


SCRAPING = ScrapingConfig()

# 投資金額（円）。--budget で上書き可能。
DEFAULT_BUDGET = 15000
BUDGET_MIN = 10000
BUDGET_MAX = 20000


def get_profile(race_name: str) -> RaceProfile:
    """レース名からプロファイルを取得。未登録なら安田記念をベースに警告。"""
    if race_name in RACE_PROFILES:
        return RACE_PROFILES[race_name]
    raise KeyError(
        f"未登録のレース: {race_name!r}. "
        f"config.RACE_PROFILES に追加してください。登録済み: {list(RACE_PROFILES)}"
    )
