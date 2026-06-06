"""騎手スコア（0-100）。

当該コース・距離での騎手の勝率・複勝率から評価する。
サンプル数が少ない場合はベイズ的に中立へ縮約する。
"""
from __future__ import annotations

from config import RaceProfile
from models import Horse

NEUTRAL = 50.0
# 縮約の強さ（この件数を「事前」として中立率に寄せる）
PRIOR_STARTS = 20
PRIOR_WIN_RATE = 0.08   # 全体平均的な勝率
PRIOR_SHOW_RATE = 0.25  # 全体平均的な複勝率


def score(horse: Horse, profile: RaceProfile) -> float:
    st = horse.jockey_stats
    if st.starts == 0:
        return NEUTRAL

    n = st.starts
    # ベイズ縮約（小サンプルを平均へ寄せる）
    win_rate = (st.wins + PRIOR_STARTS * PRIOR_WIN_RATE) / (n + PRIOR_STARTS)
    show_rate = (st.shows + PRIOR_STARTS * PRIOR_SHOW_RATE) / (n + PRIOR_STARTS)

    # トップ騎手帯（勝率25%/複勝率55%）で概ね満点になるようスケール
    win_component = min(win_rate / 0.25, 1.0)
    show_component = min(show_rate / 0.55, 1.0)

    raw = 0.6 * win_component + 0.4 * show_component
    return round(raw * 100.0, 1)
