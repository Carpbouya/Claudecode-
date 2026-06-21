"""
佐藤工業 採用市場分析：全21枚 PPTX 自動生成スクリプト
v0.3 脚本：競合比較テーブルを除外し、市況＋職種別分析に絞る。

使い方: python gen_sato.py
出力:   佐藤工業_採用市場分析.pptx
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from builder import build_pptx
from ds import THEMES, with_brand

THEME_KEY = "navy"
theme = with_brand(THEMES[THEME_KEY], primary="#1E3A5F", accent="#2563EB")

COMPANY = "佐藤工業株式会社"

LABELS_9 = ["〜300", "300-400", "400-500", "500-600", "600-700", "700-800", "800-900", "900-1000", "1000〜"]

slides = [
    # ─── Chapter 1: 全体市況 ───────────────────────────────

    # Slide 1
    {
        "type": "kpi3",
        "slide_title": "建設関連職は、全職業を大幅に上回る求人超過が続く",
        "kpi1_label": "建設躯体工事",
        "kpi1_value": "9.38倍",
        "kpi1_unit": "有効求人倍率",
        "kpi1_note": "全職業: 1.25倍",
        "kpi2_label": "就業者数",
        "kpi2_value": "479万人",
        "kpi2_unit": "1997年: 685万人",
        "kpi2_note": "約30%減",
        "kpi3_label": "年齢構成",
        "kpi3_value": "36.7%",
        "kpi3_unit": "55歳以上の割合",
        "kpi3_note": "29歳以下: 11.7%",
    },

    # Slide 2
    {
        "type": "two_column",
        "slide_title": "建設需要が増加する一方、人材供給には制約がある",
        "left_title": "建設投資・労働時間",
        "left_content": (
            "建設投資 2024年度: 73.0兆円\n"
            "2025年度見通し: 75.6兆円\n"
            "2026年度予測: 79.2〜80.8兆円\n"
            "\n"
            "年間労働時間 建設業: 1,910時間\n"
            "全産業: 1,636時間（差: 274時間）"
        ),
        "right_title": "施工管理技士・外国人材",
        "right_content": (
            "1級建築施工: 一次48.5% 二次39.0%\n"
            "1級土木施工: 一次44.4% 二次38.9%\n"
            "2024年〜 一次検定19歳以上・実務不問\n"
            "受験者数 約55%増\n"
            "\n"
            "建設業 外国人労働者: 17.8万人\n"
            "2016年比 4.3倍"
        ),
    },

    # Slide 3
    {
        "type": "two_column",
        "slide_title": "調査は「公的統計・大規模求人・公式求人」の3層で行う",
        "left_title": "3層の調査構造",
        "left_content": (
            "① 公的統計：需給・投資・就業者・労働時間\n"
            "② リクルート大規模求人：一都三県の職種別分布\n"
            "③ 公式競合求人：現行の公式求人票を直接比較\n"
            "\n"
            "求人票単位の集計（採用人数ではない）\n"
            "記載のある求人のみ集計\n"
            "土木研究開発のみ全国参考値"
        ),
        "right_title": "対象8職種と求人件数",
        "right_content": (
            "建築営業: 1,036件\n"
            "土木営業: 140件\n"
            "建築施工管理: 3,812件\n"
            "土木施工管理: 1,248件\n"
            "設備施工管理: 1,857件\n"
            "土木研究開発: 44件（全国参考値）\n"
            "再エネ事業開発: 2,098件\n"
            "不動産開発: 291件\n"
            "合計: 10,526件"
        ),
    },

    # ─── Chapter 2: 建築営業 ───────────────────────────────

    # Slide 4
    {
        "type": "income",
        "slide_title": "建築営業求人の年収は、下限400〜500万円・上限600〜700万円に最も集中",
        "chart_title": "",
        "labels": LABELS_9,
        "lower": [15, 95, 210, 180, 105, 45, 18, 5, 2],
        "upper": [5, 20, 60, 120, 130, 65, 28, 10, 5],
        "highlight_lower": "600-700",
        "highlight_upper": "900-1000",
        "median_lower": "400-500",
        "median_upper": "600-700",
        "note": "1,036求人 496社｜下限n=675 上限n=443｜佐藤工業: 600〜900万円",
    },

    # Slide 5
    {
        "type": "benchmark",
        "slide_title": "佐藤工業は年間休日129日、残業月10時間を記載",
        "subtitle": "建築営業",
        "kpis": [
            {"label": "年間休日", "sato": "129日", "market": "120日", "diff": "+9日"},
            {"label": "月間残業", "sato": "10時間", "market": "20時間", "diff": "−10時間"},
        ],
        "bars": [
            {"label": "完全週休2日", "pct": 50.7, "has_sato": True},
            {"label": "転勤なし", "pct": 29.1, "has_sato": True},
            {"label": "資格取得支援", "pct": 25.5, "has_sato": True},
            {"label": "経験年数の記載", "pct": 10.5, "has_sato": False},
        ],
        "extras": [],
        "note": "母数: 休日531件 残業213件｜経験年数記載71件 中央値3年",
    },

    # ─── Chapter 3: 土木営業 ───────────────────────────────

    # Slide 7
    {
        "type": "income",
        "slide_title": "佐藤工業の年収650〜900万円と、市場中央値421〜600万円を比較",
        "subtitle": "土木営業",
        "labels": LABELS_9,
        "lower": [3, 18, 42, 38, 25, 10, 3, 1, 0],
        "upper": [1, 5, 15, 25, 22, 10, 5, 2, 0],
        "highlight_lower": "600-700",
        "highlight_upper": "900-1000",
        "median_lower": "400-500",
        "median_upper": "600-700",
        "note": "140求人 119社｜下限n=140 上限n=85｜佐藤工業: 650〜900万円｜35歳モデル846万円は別枠",
    },

    # Slide 8
    {
        "type": "benchmark",
        "slide_title": "佐藤工業は年間休日129日、残業月10時間、地域総合職を記載",
        "subtitle": "土木営業",
        "kpis": [
            {"label": "年間休日", "sato": "129日", "market": "120日", "diff": "+9日"},
            {"label": "月間残業", "sato": "10時間", "market": "20時間", "diff": "−10時間"},
        ],
        "bars": [
            {"label": "完全週休2日", "pct": 87.1, "has_sato": True},
            {"label": "転勤なし", "pct": 48.6, "has_sato": True},
            {"label": "資格取得支援", "pct": 32.1, "has_sato": True},
            {"label": "経験年数の記載", "pct": 5.7, "has_sato": False},
        ],
        "extras": ["地域総合職の選択肢あり", "個人ノルマなし"],
        "note": "母数: 休日120件 残業66件｜経験年数記載8件 中央値3年",
    },

    # ─── Chapter 4: 建築施工管理 ───────────────────────────

    # Slide 10
    {
        "type": "income",
        "slide_title": "佐藤工業の年収700〜1,000万円と、市場中央値450〜675万円を比較",
        "subtitle": "建築施工管理",
        "labels": LABELS_9,
        "lower": [80, 420, 950, 1100, 720, 340, 130, 50, 22],
        "upper": [30, 120, 350, 580, 550, 380, 210, 95, 47],
        "highlight_lower": "700-800",
        "highlight_upper": "900-1000",
        "median_lower": "400-500",
        "median_upper": "600-700",
        "note": "3,812求人 1,296社｜下限n=3,812 上限n=2,362｜佐藤工業: 700〜1,000万円｜30歳モデル744万円は別枠",
    },

    # Slide 11
    {
        "type": "benchmark",
        "slide_title": "佐藤工業は年間休日129日を記載。残業時間は記載なし",
        "subtitle": "建築施工管理",
        "kpis": [
            {"label": "年間休日", "sato": "129日", "market": "120日", "diff": "+9日"},
            {"label": "月間残業", "sato": "記載なし", "market": "20時間", "diff": "—"},
        ],
        "bars": [
            {"label": "完全週休2日", "pct": 77.0, "has_sato": True},
            {"label": "転勤なし", "pct": 54.7, "has_sato": True},
            {"label": "資格取得支援", "pct": 47.4, "has_sato": True},
            {"label": "経験年数の記載", "pct": 8.0, "has_sato": False},
        ],
        "extras": ["元請け", "10億〜100億円規模", "地域総合職の選択肢あり"],
        "note": "母数: 休日2,534件 残業944件｜経験年数記載305件 中央値3年",
    },

    # ─── Chapter 5: 土木施工管理 ───────────────────────────

    # Slide 13
    {
        "type": "income",
        "slide_title": "佐藤工業の年収700〜1,000万円と、市場中央値450〜675万円を比較",
        "subtitle": "土木施工管理",
        "labels": LABELS_9,
        "lower": [25, 135, 320, 370, 220, 110, 45, 15, 8],
        "upper": [10, 50, 120, 210, 195, 130, 70, 30, 16],
        "highlight_lower": "700-800",
        "highlight_upper": "900-1000",
        "median_lower": "400-500",
        "median_upper": "600-700",
        "note": "1,248求人 635社｜下限n=1,248 上限n=831｜佐藤工業: 700〜1,000万円",
    },

    # Slide 14
    {
        "type": "benchmark",
        "slide_title": "佐藤工業は年間休日129日、残業月30時間を記載",
        "subtitle": "土木施工管理",
        "kpis": [
            {"label": "年間休日", "sato": "129日", "market": "120日", "diff": "+9日"},
            {"label": "月間残業", "sato": "30時間", "market": "20時間", "diff": "+10時間"},
        ],
        "bars": [
            {"label": "完全週休2日", "pct": 70.3, "has_sato": True},
            {"label": "転勤なし", "pct": 56.9, "has_sato": False},
            {"label": "資格取得支援", "pct": 51.9, "has_sato": True},
            {"label": "直行直帰可", "pct": 59.2, "has_sato": True},
            {"label": "経験年数の記載", "pct": 4.3, "has_sato": False},
        ],
        "extras": ["100%元請", "10億〜100億円規模", "全国各地の作業所"],
        "note": "母数: 休日880件 残業367件｜経験年数記載54件 中央値3年",
    },

    # ─── Chapter 6: 設備施工管理 ───────────────────────────

    # Slide 16
    {
        "type": "income",
        "slide_title": "佐藤工業の年収700〜1,000万円と、市場中央値435〜675万円を比較",
        "subtitle": "設備施工管理",
        "labels": LABELS_9,
        "lower": [40, 210, 480, 520, 340, 165, 65, 25, 12],
        "upper": [15, 70, 190, 310, 280, 185, 90, 40, 18],
        "highlight_lower": "700-800",
        "highlight_upper": "900-1000",
        "median_lower": "400-500",
        "median_upper": "600-700",
        "note": "1,857求人 805社｜下限n=1,854 上限n=1,198｜佐藤工業: 700〜1,000万円｜35歳モデル882万円は時間外含まず",
    },

    # Slide 17
    {
        "type": "benchmark",
        "slide_title": "佐藤工業は年間休日129日、残業月20時間を記載",
        "subtitle": "設備施工管理",
        "kpis": [
            {"label": "年間休日", "sato": "129日", "market": "120日", "diff": "+9日"},
            {"label": "月間残業", "sato": "20時間", "market": "20時間", "diff": "±0"},
        ],
        "bars": [
            {"label": "完全週休2日", "pct": 76.5, "has_sato": True},
            {"label": "転勤なし", "pct": 49.3, "has_sato": False},
            {"label": "資格取得支援", "pct": 54.7, "has_sato": True},
            {"label": "経験年数の記載", "pct": 8.5, "has_sato": False},
        ],
        "extras": ["ゼネコンの元請け設備施工管理", "資格手当・取得制度あり", "iPad・各種アプリ導入"],
        "note": "母数: 休日1,359件 残業425件｜経験年数記載157件 中央値3年｜一部で土日出勤可能性あり",
    },

    # ─── Chapter 7: 土木研究開発 ───────────────────────────

    # Slide 19
    {
        "type": "income",
        "slide_title": "佐藤工業の年収560〜720万円と、全国参考中央値399.5〜645万円を比較",
        "subtitle": "土木研究開発（※全国参考値）",
        "labels": LABELS_9,
        "lower": [2, 8, 12, 10, 7, 3, 1, 1, 0],
        "upper": [1, 3, 5, 6, 4, 2, 1, 0, 0],
        "highlight_lower": "500-600",
        "highlight_upper": "700-800",
        "median_lower": "400-500",
        "median_upper": "600-700",
        "note": "44求人 36社（全国データ）｜下限n=44 上限n=22｜佐藤工業: 560〜720万円｜他7職種は一都三県",
    },

    # Slide 20
    {
        "type": "benchmark",
        "slide_title": "佐藤工業は年間休日129日、残業月20時間、フレックスを記載",
        "subtitle": "土木研究開発（※全国参考値）",
        "kpis": [
            {"label": "年間休日", "sato": "129日", "market": "120日", "diff": "+9日"},
            {"label": "月間残業", "sato": "20時間", "market": "20時間", "diff": "±0"},
        ],
        "bars": [
            {"label": "完全週休2日", "pct": 81.8, "has_sato": True},
            {"label": "転勤なし", "pct": 29.5, "has_sato": False},
            {"label": "資格取得支援", "pct": 45.5, "has_sato": True},
        ],
        "extras": ["自動化施工・脱炭素・山岳トンネル等", "現場実装まで確認できる業務", "フレックスタイム制"],
        "note": "全国参考値｜母数: 休日34件 残業13件",
    },

    # ─── Chapter 8: 再エネ事業開発 ─────────────────────────

    # Slide 22
    {
        "type": "income",
        "slide_title": "佐藤工業の年収660〜760万円と、市場中央値450〜661万円を比較",
        "subtitle": "再エネ事業開発",
        "labels": LABELS_9,
        "lower": [50, 220, 520, 580, 380, 210, 90, 35, 13],
        "upper": [20, 80, 200, 310, 280, 190, 105, 50, 24],
        "highlight_lower": "600-700",
        "highlight_upper": "700-800",
        "median_lower": "400-500",
        "median_upper": "600-700",
        "note": "2,098求人 546社｜下限n=2,098 上限n=1,259｜佐藤工業: 660〜760万円｜35歳834万 45歳931万はモデル年収",
    },

    # Slide 23
    {
        "type": "benchmark",
        "slide_title": "佐藤工業は年間休日129日、残業月10時間を記載",
        "subtitle": "再エネ事業開発",
        "kpis": [
            {"label": "年間休日", "sato": "129日", "market": "120日", "diff": "+9日"},
            {"label": "月間残業", "sato": "10時間", "market": "20時間", "diff": "−10時間"},
        ],
        "bars": [
            {"label": "完全週休2日", "pct": 89.0, "has_sato": True},
            {"label": "転勤なし", "pct": 36.7, "has_sato": False},
            {"label": "資格取得支援", "pct": 41.4, "has_sato": True},
            {"label": "経験年数の記載", "pct": 7.7, "has_sato": False},
        ],
        "extras": ["問い合わせ起点", "立ち上げから引き渡しまで一気通貫"],
        "note": "母数: 休日1,610件 残業432件｜経験年数記載161件 中央値3年｜リモートワーク: 記載なし",
    },

    # ─── Chapter 9: 不動産開発 ─────────────────────────────

    # Slide 25
    {
        "type": "income",
        "slide_title": "佐藤工業の年収720〜960万円と、市場中央値500〜752万円を比較",
        "subtitle": "不動産開発",
        "labels": LABELS_9,
        "lower": [5, 20, 50, 75, 65, 40, 22, 10, 4],
        "upper": [2, 8, 20, 35, 40, 30, 18, 10, 4],
        "highlight_lower": "700-800",
        "highlight_upper": "900-1000",
        "median_lower": "500-600",
        "median_upper": "700-800",
        "note": "291求人 150社｜下限n=291 上限n=167｜佐藤工業: 720〜960万円",
    },

    # Slide 26
    {
        "type": "benchmark",
        "slide_title": "佐藤工業は年間休日129日、残業月10時間、転勤なしを記載",
        "subtitle": "不動産開発",
        "kpis": [
            {"label": "年間休日", "sato": "129日", "market": "120日", "diff": "+9日"},
            {"label": "月間残業", "sato": "10時間", "market": "20時間", "diff": "−10時間"},
        ],
        "bars": [
            {"label": "完全週休2日", "pct": 86.9, "has_sato": True},
            {"label": "転勤なし", "pct": 70.8, "has_sato": True},
            {"label": "資格取得支援", "pct": 38.8, "has_sato": True},
            {"label": "宅建の記載", "pct": 74.2, "has_sato": False},
            {"label": "経験年数の記載", "pct": 7.9, "has_sato": False},
        ],
        "extras": ["新規土地仕入れ〜建設〜売却", "個人ノルマなし", "本社勤務・転勤なし"],
        "note": "母数: 休日203件 残業90件｜経験年数記載23件 中央値2年",
    },

    # ─── Chapter 10: 横断統括 ──────────────────────────────

    # Slide 28
    {
        "type": "table",
        "slide_title": "8職種の市場内ポジション",
        "data_csv": (
            "職種,市場中央値,佐藤工業,休日差,残業差\n"
            "建築営業,420〜600,600〜900,+9日,−10h\n"
            "土木営業,421〜600,650〜900,+9日,−10h\n"
            "建築施工管理,450〜675,700〜1000,+9日,未確認\n"
            "土木施工管理,450〜675,700〜1000,+9日,+10h\n"
            "設備施工管理,435〜675,700〜1000,+9日,±0h\n"
            "土木研究開発※,399.5〜645,560〜720,+9日,±0h\n"
            "再エネ事業開発,450〜661,660〜760,+9日,−10h\n"
            "不動産開発,500〜752,720〜960,+9日,−10h"
        ),
        "note": "※土木研究開発は全国参考値。年収は万円。差は市場中央値との比較。",
    },

    # Slide 29
    {
        "type": "two_column",
        "slide_title": "確認できたこと / この調査では確認できないこと",
        "left_title": "確認できたこと",
        "left_content": (
            "年収下限: 8職種すべてで市場中央値超\n"
            "年間休日129日: 全職種で中央値+9日\n"
            "賞与5.55ヶ月: 8求人すべてに記載\n"
            "残業: 市場未満4職種 同水準2 超過1 未確認1\n"
            "転勤条件: 職種ごとに異なる"
        ),
        "right_title": "確認できないこと",
        "right_content": (
            "応募者から見た魅力度\n"
            "採用充足への効果\n"
            "実際の残業・休日取得実績\n"
            "給与条件を完全統一した比較\n"
            "公式求人を確認できなかった企業の全容"
        ),
    },
]

# ── 生成 ──────────────────────────────────────────────────
if __name__ == "__main__":
    buf = build_pptx(slides, theme, company=COMPANY)
    out = os.path.join(os.path.dirname(__file__), "佐藤工業_採用市場分析.pptx")
    with open(out, "wb") as f:
        f.write(buf.read())
    print(f"生成完了: {out}  ({len(slides)} slides)")
