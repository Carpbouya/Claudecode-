"""印付き馬の根拠テキスト生成（ターミナル・HTML 共用）。"""
from __future__ import annotations

from config import RaceProfile
from models import Horse, RaceData


def _record_at_condition(horse: Horse, profile: RaceProfile) -> tuple[int, int, int, int]:
    """当該条件での [勝-連対-複勝外-着外] 風の集計を返す。"""
    rel = [
        r for r in horse.past_results
        if r.surface == profile.surface
        and abs(r.distance - profile.distance) <= profile.distance_tolerance
    ]
    wins = sum(1 for r in rel if r.finish == 1)
    second = sum(1 for r in rel if r.finish == 2)
    third = sum(1 for r in rel if r.finish == 3)
    out = len(rel) - wins - second - third
    return wins, second, third, out


def build_rationale(horse: Horse, profile: RaceProfile) -> str:
    """1 頭分の根拠テキスト。"""
    w, s, t, o = _record_at_condition(horse, profile)
    n = w + s + t + o
    parts: list[str] = []
    if n:
        show_rate = (w + s + t) / n * 100
        parts.append(
            f"{profile.course}{profile.surface}{profile.distance}m "
            f"[{w}-{s}-{t}-{o}] 複勝率{show_rate:.0f}%"
        )
    parts.append(f"{horse.jockey}騎手（騎手スコア{horse.scores.get('jockey', 0):.0f}）")
    parts.append(f"調教{horse.training_grade}評価")

    if horse.mark == "▲":
        parts.append(
            f"単勝{horse.win_odds:.0f}倍に対し推定勝率{horse.estimated_win_prob*100:.0f}%、"
            f"期待値{horse.expected_value:.1f}倍の穴馬"
        )
    return " / ".join(parts)


def build_summaries(race: RaceData, profile: RaceProfile, marks) -> list[dict]:
    """印が付いた馬の根拠サマリーを順に返す。"""
    ordered = [m for m in (marks.honmei, marks.taikou, marks.ana, marks.osae) if m]
    out: list[dict] = []
    seen = set()
    for h in ordered:
        if h.number in seen:
            continue
        seen.add(h.number)
        out.append({
            "mark": h.mark,
            "number": h.number,
            "name": h.name,
            "total": h.total_score,
            "text": build_rationale(h, profile),
        })
    return out
