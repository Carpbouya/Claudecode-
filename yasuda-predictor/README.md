# 安田記念 競馬予想ソフト（yasuda-predictor）

netkeiba のデータを起点に、5 要素の重み付きスコアリングで各馬を客観評価し、
**買い目（馬券種・組み合わせ・金額配分）まで自動生成**する競馬予想ソフトです。
GI 全般へ展開できる構造（`config.RACE_PROFILES`）になっています。

## セットアップ

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## 使い方

```bash
# 安田記念の予想（race_id 未登録時はサンプルデータにフォールバック）
python main.py --race "安田記念" --year 2026

# netkeiba の URL を直接指定（実データ取得）
python main.py --url "https://race.netkeiba.com/race/shutuba.html?race_id=XXXXXXXX"

# サンプルデータで全機能をデモ（ネット接続不要）
python main.py --race "安田記念" --year 2026 --sample

# オプション
--budget 20000     # 投資金額（円, デフォルト 15,000 / 推奨 10,000〜20,000）
--output html      # 出力形式: html / text / both（デフォルト both）
--no-cache         # キャッシュを使わず再取得
--open             # 生成した HTML をブラウザで開く
-v                 # 詳細ログ
```

ターミナルにスコア表・買い目・根拠を表示し、`output/<レース名>_<年>.html` に
HTML レポート（スコア一覧・棒グラフ・買い目・根拠／印刷対応）を出力します。

## スコアリング（5 要素・重みは `config.py` で調整可能）

| 要素 | 重み | 概要 | 実装 |
|------|------|------|------|
| 過去成績 | 30% | 当該距離帯・同サーフェスの勝率/連対率/複勝率（直近重視） | `scorer/past_results.py` |
| 騎手 | 20% | 当該コースの勝率・複勝率（小サンプルはベイズ縮約） | `scorer/jockey.py` |
| 調教 | 20% | 評価 A/B/C ＋ 出走馬中のタイム偏差補正 | `scorer/training.py` |
| 血統 | 15% | 父の当該条件産駒成績 ＋ 母父ボーナス | `scorer/bloodline.py` |
| 期待値（穴） | 15% | 期待値 = 単勝オッズ × 推定勝率（乖離が大きいほど加点） | `scorer/odds_value.py` |

`総合スコア = Σ(要素スコア × 重み)`。期待値スコアの推定勝率は、他 4 要素の
合成スコアをソフトマックスで分布化して求めます（`scorer/engine.py`）。

## 買い目生成ロジック（`buyer/ticket_generator.py`）

総合スコアと期待値から ◎本命・○対抗・▲穴・△押さえ を付与し、分布に応じて
馬券種を自動選択します。

| 条件 | 馬券種 |
|------|--------|
| 穴馬の期待値スコアが高い | 3連複 ◎軸＋穴1頭 流し |
| 上位2頭のスコア差が大きい | 馬連 |
| 上位3頭が団子 | ワイド3点 |
| 全体的に混戦 | 3連複フォーメーション |

配当・期待値は市場オッズ由来の **概算（推定）** です。

## GI 展開

`config.RACE_PROFILES` にレース特性（距離・コース・サーフェス・重み）を追加する
だけで対応できます。スコアリングロジック本体は共通利用されます。

```python
RACE_PROFILES = {
    "安田記念": RaceProfile("安田記念", 1600, "東京", "芝", ScoreWeights(...)),
    "ダービー": RaceProfile("ダービー", 2400, "東京", "芝", ScoreWeights(...)),
    "有馬記念": RaceProfile("有馬記念", 2500, "中山", "芝", ScoreWeights(...)),
}
```

## スクレイピングに関する注意（規約配慮）

netkeiba のスクレイピングは利用規約上グレーゾーンです。本実装では以下を遵守します。

- リクエスト間隔を最低 2.5 秒空ける（`config.ScrapingConfig.min_interval_sec`）
- User-Agent を明示
- 取得結果をキャッシュ（`scraper/cache.py`, デフォルト 6 時間）して再取得を抑制
- 取得失敗時はスキップしてログ出力し、処理を継続（サンプルへフォールバック）

個人利用・自己責任の範囲でご利用ください。過剰なアクセスは行わないでください。

## 実装状況メモ

- 出馬表（馬番・枠番・馬名・騎手）と単勝オッズの取得・パースを実装済み
  （`scraper/netkeiba.py`）。実 race_id は `config.KNOWN_RACE_IDS` への登録、
  または `--url` 指定で利用します。
- 過去成績・騎手コース成績・調教・血統など馬個別ページ由来の詳細データ取得は、
  ライブサイト構造に依存するため拡張ポイントとして分離しています。未取得の要素は
  スコアが中立値（50〜55 点）に縮約され、パイプラインは継続します。
- `--sample` で全要素を含むフィクスチャを用い、スコアリング〜買い目〜レポートの
  全工程を接続不要で検証できます。

## ディレクトリ構成

```
yasuda-predictor/
├── main.py               # エントリポイント（argparse）
├── config.py             # 重み・レースプロファイル・スクレイピング設定
├── models.py             # ドメインモデル（Horse / RaceData ほか）
├── scraper/              # netkeiba 取得・キャッシュ・サンプル
├── scorer/               # 5 要素スコア + engine
├── buyer/                # 買い目生成
├── reporter/             # HTML/ターミナル出力（Jinja2）
├── data/cache/           # スクレイピングキャッシュ
└── output/               # 生成レポート
```
