"""血統スコア（0-100）。

種牡馬（父）の当該コース・サーフェス・距離産駒成績から評価する。
母父は補助的に加点する（適性の裏付け）。データ無しは中立値。
"""
from __future__ import annotations

from config import RaceProfile
from models import Horse

NEUTRAL = 50.0
PRIOR_RUNS = 50
PRIOR_WIN_RATE = 0.07
PRIOR_SHOW_RATE = 0.22

# 当該条件（東京芝中距離）に実績のある母父への小さなボーナス
FAVORED_BROODMARE_SIRES = {
    "サンデーサイレンス", "キングカメハメハ", "ディープインパクト",
}


def score(horse: Horse, profile: RaceProfile) -> float:
    st = horse.sire_stats
    if st.runs == 0:
        base = NEUTRAL
    else:
        n = st.runs
        win_rate = (st.wins + PRIOR_RUNS * PRIOR_WIN_RATE) / (n + PRIOR_RUNS)
        show_rate = (st.shows + PRIOR_RUNS * PRIOR_SHOW_RATE) / (n + PRIOR_RUNS)
        win_component = min(win_rate / 0.20, 1.0)
        show_component = min(show_rate / 0.50, 1.0)
        base = (0.6 * win_component + 0.4 * show_component) * 100.0

    if horse.broodmare_sire in FAVORED_BROODMARE_SIRES:
        base = min(base + 5.0, 100.0)

    return round(base, 1)
