"""スコアリングエンジン。

5 要素を 0-100 で算出し、重み付き合計（総合スコア）を求める。
期待値スコアは推定勝率に依存するため、以下の順で計算する:

  1. 過去成績 / 騎手 / 調教 / 血統 の 4 要素を算出
  2. 4 要素の重み付き合成からソフトマックスで推定勝率を算出
  3. 期待値スコア（= 単勝オッズ × 推定勝率）を算出
  4. 5 要素の重み付き合計＝総合スコア
"""
from __future__ import annotations

import math

from config import RaceProfile
from models import Horse, RaceData
from scorer import bloodline, jockey, odds_value, past_results, training

BASE_KEYS = ("past_results", "jockey", "training", "bloodline")


def _softmax_probs(values: list[float], temperature: float = 12.0) -> list[float]:
    """合成スコアを勝率分布へ変換。temperature が小さいほど尖る。"""
    scaled = [v / temperature for v in values]
    m = max(scaled)
    exps = [math.exp(s - m) for s in scaled]
    total = sum(exps)
    return [e / total for e in exps]


def score_race(race: RaceData, profile: RaceProfile) -> RaceData:
    """レース内の全馬にスコアを付与し、総合スコア降順で並べ替える。"""
    weights = profile.weights
    horses = race.horses

    # 1. 基礎 4 要素
    for h in horses:
        h.scores["past_results"] = past_results.score(h, profile)
        h.scores["jockey"] = jockey.score(h, profile)
        h.scores["training"] = training.score(h, profile, field=horses)
        h.scores["bloodline"] = bloodline.score(h, profile)

    # 2. 基礎合成 → 推定勝率（基礎 4 要素の重み比で合成）
    base_weight_sum = sum(getattr(weights, k) for k in BASE_KEYS) or 1.0
    composites = []
    for h in horses:
        comp = sum(h.scores[k] * getattr(weights, k) for k in BASE_KEYS) / base_weight_sum
        composites.append(comp)
    probs = _softmax_probs(composites)
    for h, p in zip(horses, probs):
        h.estimated_win_prob = round(p, 4)

    # 3. 期待値スコア
    for h in horses:
        h.scores["odds_value"] = odds_value.score(h)

    # 4. 総合スコア = Σ(要素スコア × 重み)
    for h in horses:
        h.total_score = round(
            sum(h.scores[k] * getattr(weights, k) for k in h.scores),
            1,
        )

    race.horses.sort(key=lambda h: h.total_score, reverse=True)
    return race
