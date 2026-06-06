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

## スクレイピング実装と取得ページ

`scraper/parsers.py` に **I/O を持たない純粋なパース関数**を集約し、
`scraper/netkeiba.py` が HTTP 取得・レート制限・キャッシュ・取得順序を担います。
この分離により、ネット接続なしで保存 HTML に対する単体テストが可能です。

| 取得ページ | URL | 取得内容 |
|-----------|-----|---------|
| 出馬表 | `race.netkeiba.com/race/shutuba.html` | 馬番・枠番・馬名・騎手・単勝（＋ horse_id / jockey_id） |
| オッズ | `race.netkeiba.com/odds/index.html` | 最新の単勝オッズ |
| 調教 | `race.netkeiba.com/race/oikiri.html` | 調教タイム・評価（S/A/B/C → A/B/C） |
| 馬ページ | `db.netkeiba.com/horse/{id}/` | 過去成績（距離/コース/着順/頭数/人気）・血統（父・母父） |
| 種牡馬 | `db.netkeiba.com/horse/sire/{id}/` | 父のコース×サーフェス×距離帯の産駒成績 |
| 騎手 | `db.netkeiba.com/jockey/{id}/` | 当該コースの着別度数（勝率・複勝率） |

取得手順（`fetch_race`）: 出馬表 → オッズ/調教（レース全体・各 1 回）→ 各馬の
馬/種牡馬/騎手ページを取得。詳細ページの失敗は **1 件ずつ握って中立値で続行**し、
同一レースで重複する騎手・種牡馬は実行内メモで再取得を避けます。
`--no-enrich` で詳細取得を省略し出馬表＋オッズのみの高速実行も可能です。

DOM 変更への耐性として、成績テーブルは「ヘッダのラベル → 列インデックス」で
マッピングし、複数セレクタのフォールバックを用います。

## テスト

```bash
python -m unittest discover tests
```

- `tests/test_parsers.py` … 各パーサを実マークアップ準拠の HTML フィクスチャ
  （`tests/fixtures/`）で検証。空・壊れた HTML でも例外を投げず中立値を返すことも確認。
- `tests/test_scraper_orchestration.py` … `fetch_html` をスタブ化し、出馬表→
  オッズ→調教→馬/種牡馬/騎手の取得・統合、`--no-enrich`、詳細ページ失敗時の
  続行（エラー耐性）、出馬表失敗時の例外送出を検証。

## 動作環境に関する注意（ライブ取得）

本リポジトリの開発環境はネットワーク allowlist により netkeiba への到達が
ブロックされています（`Host not in allowlist`）。そのため**ライブ取得は実
ネットワーク環境での実行が必要**です。パーサーは netkeiba の DOM 構造に
忠実に実装し、上記フィクスチャ＋テストで構造解析の正しさを担保しています。

実 race_id は `config.KNOWN_RACE_IDS` への登録、または `--url` 指定で利用します
（誤った推測 ID は同梱していません）。未取得の要素はスコアが中立値（50〜55 点）に
縮約され、パイプラインは継続します。`--sample` で全要素を含むフィクスチャを用い、
スコアリング〜買い目〜レポートの全工程を接続不要で検証できます。

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
