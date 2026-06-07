"""過去成績スコア（0-100）。

当該レースの距離帯（±許容幅）・同サーフェスでの勝率・連対率・複勝率を
直近走ほど重く評価する。該当データが無い場合は中立値を返す。
"""
from __future__ import annotations

from config import RaceProfile
from models import Horse

NEUTRAL = 50.0


def score(horse: Horse, profile: RaceProfile) -> float:
    relevant = [
        r for r in horse.past_results
        if r.surface == profile.surface
        and abs(r.distance - profile.distance) <= profile.distance_tolerance
    ]
    if not relevant:
        return NEUTRAL

    # 直近ほど重い指数減衰の重み（新しい順に並んでいる前提だが順不同でも可）
    relevant = relevant[:10]
    weights = [0.85 ** i for i in range(len(relevant))]
    wsum = sum(weights)

    win = sum(w for r, w in zip(relevant, weights) if r.is_win) / wsum
    quinella = sum(w for r, w in zip(relevant, weights) if r.is_quinella) / wsum
    show = sum(w for r, w in zip(relevant, weights) if r.is_show) / wsum

    # 着順の質（人気を上回る好走を加点）: 着順を頭数で正規化
    finish_quality = sum(
        w * (1.0 - (r.finish - 1) / max(r.field_size - 1, 1))
        for r, w in zip(relevant, weights)
    ) / wsum

    raw = 0.40 * win + 0.25 * quinella + 0.20 * show + 0.15 * finish_quality
    return round(min(raw * 100.0, 100.0), 1)
