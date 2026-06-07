"""買い目生成。

総合スコアと期待値から印（◎○▲△）を付与し、スコア分布に応じて馬券種を
自動選択、指定予算内で金額配分する。配当・期待値は推定値（市場オッズ由来）。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from itertools import permutations

from models import Horse, RaceData

# 穴（▲）とみなす最低単勝オッズ
ANA_ODDS_MIN = 7.0
# 上位 2 頭のスコア差が「大きい」とみなす閾値
GAP_LARGE = 8.0
# 上位 3 頭が「団子」とみなすスコア幅
CLUSTER_SPREAD = 5.0
# 穴スコアが「高い」とみなす閾値
ANA_VALUE_HIGH = 70.0

# 馬券種ごとの配当推定係数（市場オッズ積に対する控除後の概算倍率）
PAYOUT_COEF = {"馬連": 0.40, "馬単": 0.85, "ワイド": 0.13, "3連複": 0.075}


@dataclass
class MarkedHorses:
    honmei: Horse                 # ◎ 本命
    taikou: Horse                 # ○ 対抗
    ana: Horse | None = None      # ▲ 穴
    osae: Horse | None = None     # △ 押さえ


@dataclass
class TicketProposal:
    bet_type: str
    combos: list[tuple[int, ...]]
    per_amount: int
    total_amount: int
    payout_low: int
    payout_high: int
    expected_value: float          # 期待値倍率（>1 で妙味）
    marks: MarkedHorses
    rationale: str = ""
    combo_label: str = field(default="")


# -- 印の付与 ---------------------------------------------------------------
def assign_marks(race: RaceData) -> MarkedHorses:
    horses = race.horses  # 総合スコア降順前提
    honmei, taikou = horses[0], horses[1]

    ana_candidates = [
        h for h in horses[1:6]
        if h is not taikou and h.win_odds >= ANA_ODDS_MIN
    ]
    ana = max(ana_candidates, key=lambda h: h.scores.get("odds_value", 0)) if ana_candidates else None

    used_numbers = {h.number for h in (honmei, taikou, ana) if h}
    osae = next((h for h in horses[2:6] if h.number not in used_numbers), None)

    honmei.mark, taikou.mark = "◎", "○"
    if ana:
        ana.mark = "▲"
    if osae and osae.mark == "":
        osae.mark = "△"
    return MarkedHorses(honmei, taikou, ana, osae)


# -- ヘルパ -----------------------------------------------------------------
def _odds(race: RaceData, number: int) -> float:
    for h in race.horses:
        if h.number == number:
            return h.win_odds
    return 0.0


def _prob(race: RaceData, number: int) -> float:
    for h in race.horses:
        if h.number == number:
            return h.estimated_win_prob
    return 0.0


def _harville_unordered(probs: list[float]) -> float:
    """指定馬が（順不同で）上位に全て入る確率を Harville モデルで近似。"""
    total = 0.0
    for perm in permutations(probs):
        p, remaining = 1.0, 1.0
        ok = True
        for pi in perm:
            denom = remaining
            if denom <= 0:
                ok = False
                break
            p *= pi / denom
            remaining -= pi
        if ok:
            total += p
    return min(total, 1.0)


def _payout_multiple(bet_type: str, race: RaceData, combo: tuple[int, ...]) -> float:
    coef = PAYOUT_COEF.get(bet_type, 0.1)
    prod = 1.0
    for n in combo:
        prod *= max(_odds(race, n), 1.0)
    return prod * coef


def _round100(x: float) -> int:
    return int(round(x / 100.0)) * 100


# -- 馬券種選択 -------------------------------------------------------------
def select_bet_type(race: RaceData, marks: MarkedHorses) -> tuple[str, list[tuple[int, ...]], str, str]:
    """(馬券種, 組み合わせ, 組み合わせ表記, 選択根拠) を返す。"""
    h = race.horses
    gap = h[0].total_score - h[1].total_score
    spread = h[0].total_score - h[2].total_score
    hon, tai = marks.honmei.number, marks.taikou.number
    ana = marks.ana.number if marks.ana else None

    # 1) 穴スコアが高い → 3連複 ◎○▲ + 穴1頭 流し
    if marks.ana and marks.ana.scores.get("odds_value", 0) >= ANA_VALUE_HIGH:
        partners = [tai, ana]
        extra = next((x.number for x in h[2:6] if x.number not in {hon, tai, ana}), None)
        if extra:
            partners.append(extra)
        combos = sorted({tuple(sorted((hon, a, b)))
                         for i, a in enumerate(partners) for b in partners[i + 1:]})
        label = f"{hon}=" + "・".join(str(p) for p in partners) + "（◎軸 流し）"
        return "3連複", combos, label, "穴馬の期待値が高く、◎軸からの3連複流しで配当妙味を狙う"

    # 2) 上位2頭のスコア差が大きい → 馬連（◎→○）
    if gap >= GAP_LARGE:
        return "馬連", [tuple(sorted((hon, tai)))], f"{hon}-{tai}", \
            f"上位2頭のスコア差が大きい（{gap:.1f}点）ため、◎○の2頭で堅く仕留める"

    # 3) 上位3頭が団子 → ワイド3点
    if spread <= CLUSTER_SPREAD:
        third = h[2].number
        combos = [tuple(sorted((hon, tai))), tuple(sorted((hon, third))), tuple(sorted((tai, third)))]
        return "ワイド", combos, f"{hon}-{tai} / {hon}-{third} / {tai}-{third}", \
            f"上位3頭が僅差（{spread:.1f}点差）。ワイド3点で取りこぼしを防ぐ"

    # 4) 混戦 → 3連複フォーメーション（上位4頭 BOX 相当）
    nums = [x.number for x in h[:4]]
    combos = sorted({tuple(sorted(c)) for c in permutations(nums, 3)})
    label = "・".join(str(n) for n in nums) + " BOX"
    return "3連複", combos, label, "全体的に混戦。上位4頭のフォーメーションで広く押さえる"


# -- 金額配分 ---------------------------------------------------------------
def allocate(combos: list[tuple[int, ...]], budget: int) -> tuple[int, int]:
    """均等配分（100 円単位）。(1点あたり金額, 合計) を返す。"""
    n = len(combos)
    per = _round100(budget / n)
    per = max(per, 100)
    return per, per * n


# -- 期待値・配当推定 -------------------------------------------------------
def estimate(race: RaceData, bet_type: str, combos: list[tuple[int, ...]],
             per_amount: int) -> tuple[int, int, float]:
    """(推定配当 下限, 上限, 期待値倍率) を返す。"""
    payouts: list[float] = []
    ev_numerator = 0.0
    for combo in combos:
        mult = _payout_multiple(bet_type, race, combo)
        payout_yen = per_amount * mult
        payouts.append(payout_yen)

        probs = [_prob(race, n) for n in combo]
        if bet_type in ("馬連", "馬単", "ワイド"):
            hit = _harville_unordered(probs[:2])
        else:  # 3連複
            hit = _harville_unordered(probs)
        ev_numerator += hit * payout_yen

    total = per_amount * len(combos)
    ev = ev_numerator / total if total else 0.0
    return _round100(min(payouts)), _round100(max(payouts)), round(ev, 2)


# -- エントリ ---------------------------------------------------------------
def generate(race: RaceData, budget: int) -> TicketProposal:
    marks = assign_marks(race)
    bet_type, combos, label, rationale = select_bet_type(race, marks)
    per, total = allocate(combos, budget)
    low, high, ev = estimate(race, bet_type, combos, per)
    return TicketProposal(
        bet_type=bet_type,
        combos=combos,
        per_amount=per,
        total_amount=total,
        payout_low=low,
        payout_high=high,
        expected_value=ev,
        marks=marks,
        rationale=rationale,
        combo_label=label,
    )
