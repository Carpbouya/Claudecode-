"""安田記念 競馬予想ソフト — エントリポイント。

使用例:
    python main.py --race "安田記念" --year 2026
    python main.py --url "https://race.netkeiba.com/race/shutuba.html?race_id=XXXXXXXX"
    python main.py --race "安田記念" --year 2026 --budget 20000 --output html
    python main.py --race "安田記念" --year 2026 --sample      # サンプルデータで実行
    python main.py --race "安田記念" --year 2026 --no-cache    # キャッシュ無効
"""
from __future__ import annotations

import argparse
import logging
import sys
import webbrowser

import config
from buyer import ticket_generator
from reporter import html_report
from scorer import engine
from scraper import netkeiba


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="yasuda-predictor",
        description="netkeiba のデータからスコアリングして買い目を自動生成する競馬予想ソフト",
    )
    p.add_argument("--race", help="レース名（例: 安田記念）", default="安田記念")
    p.add_argument("--year", type=int, default=2026, help="開催年（デフォルト: 2026）")
    p.add_argument("--url", help="netkeiba のレース URL（race_id を含む）")
    p.add_argument("--budget", type=int, default=config.DEFAULT_BUDGET,
                   help=f"投資金額（円, デフォルト: {config.DEFAULT_BUDGET}）")
    p.add_argument("--output", choices=["html", "text", "both"], default="both",
                   help="出力形式（デフォルト: both）")
    p.add_argument("--no-cache", action="store_true", help="キャッシュを使わず再取得")
    p.add_argument("--sample", action="store_true",
                   help="サンプルデータで実行（ネット接続不要・デモ用）")
    p.add_argument("--open", action="store_true", help="生成した HTML をブラウザで開く")
    p.add_argument("-v", "--verbose", action="store_true", help="詳細ログを表示")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="[%(levelname)s] %(name)s: %(message)s",
    )

    if not (config.BUDGET_MIN <= args.budget <= config.BUDGET_MAX) and not args.sample:
        print(f"⚠ 予算 {args.budget:,}円 は推奨範囲外です "
              f"（{config.BUDGET_MIN:,}〜{config.BUDGET_MAX:,}円）。続行します。", file=sys.stderr)

    # レースプロファイル
    try:
        profile = config.get_profile(args.race)
    except KeyError as exc:
        print(f"エラー: {exc}", file=sys.stderr)
        return 2

    # Phase 1: データ取得
    race = netkeiba.get_race_data(
        profile, args.year, url=args.url,
        use_cache=not args.no_cache, use_sample=args.sample,
    )
    if not race.horses:
        print("エラー: 出走馬データを取得できませんでした。", file=sys.stderr)
        return 1

    # Phase 2: スコアリング
    engine.score_race(race, profile)

    # Phase 3: 買い目生成
    proposal = ticket_generator.generate(race, args.budget)

    # Phase 4: 出力
    if args.output in ("text", "both"):
        print(html_report.terminal_summary(race, profile, proposal))

    if args.output in ("html", "both"):
        path = html_report.write_html(race, profile, proposal)
        print(f"\nHTML レポートを出力しました: {path}")
        if args.open:
            webbrowser.open(path.as_uri())

    if race.source == "sample":
        print("\n※ サンプルデータで実行しました（実データは --url 指定 "
              "または config.KNOWN_RACE_IDS への race_id 登録が必要です）。", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
