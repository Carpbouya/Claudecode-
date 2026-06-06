"""期待値スコア（穴要素, 0-100）。

期待値 EV = 単勝オッズ × 推定勝率。
市場（オッズ）の評価より自前モデルの勝率が高い馬＝EV が高い馬を加点する。
EV=1.0（損益分岐）を 50 点の中立とし、上振れで加点・下振れで減点する。

注: ``estimated_win_prob`` は engine が他 4 要素から事前に算出して設定する。
"""
from __future__ import annotations

from models import Horse

NEUTRAL = 50.0
# EV 1 単位あたりの傾き（EV=2.5 で概ね満点、EV=0.5 で 約33点）
SLOPE = 33.0


def expected_value(horse: Horse) -> float:
    if horse.win_odds <= 0:
        return 0.0
    return horse.win_odds * horse.estimated_win_prob


def score(horse: Horse) -> float:
    ev = expected_value(horse)
    horse.expected_value = round(ev, 2)
    raw = NEUTRAL + (ev - 1.0) * SLOPE
    return round(max(min(raw, 100.0), 0.0), 1)
