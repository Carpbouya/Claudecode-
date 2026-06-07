"""調教スコア（0-100）。

調教評価（A/B/C）をベースに、出走馬中での調教タイム偏差で補正する。
タイムは小さいほど速い。タイム未取得時は評価のみで算出する。
"""
from __future__ import annotations

import statistics

from config import RaceProfile
from models import Horse

GRADE_BASE = {"A": 80.0, "B": 60.0, "C": 45.0}
NEUTRAL = 55.0


def score(horse: Horse, profile: RaceProfile, field: list[Horse] | None = None) -> float:
    base = GRADE_BASE.get((horse.training_grade or "").upper(), NEUTRAL)

    if horse.training_time is None or not field:
        return round(base, 1)

    times = [h.training_time for h in field if h.training_time is not None]
    if len(times) < 2:
        return round(base, 1)

    mean = statistics.fmean(times)
    stdev = statistics.pstdev(times)
    if stdev == 0:
        return round(base, 1)

    # 速い（小さい）ほど + 偏差。±2σ で ±15 点程度補正。
    z = (mean - horse.training_time) / stdev
    adjusted = base + max(min(z, 2.0), -2.0) * 7.5
    return round(max(min(adjusted, 100.0), 0.0), 1)
