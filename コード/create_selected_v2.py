#!/usr/bin/env python3
"""
競合求人_選定比較_v2.xlsx 作成スクリプト
v1 の5カテゴリに加え、再生エネルギー事業開発・土木研究開発・不動産開発の3カテゴリを追加
"""
import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# === カラー定義 ===
NAVY_FILL    = PatternFill("solid", fgColor="1F3864")   # タイトル行（ネイビー）
HEADER_FILL  = PatternFill("solid", fgColor="404040")   # ヘッダー行（ダークグレー）
N1_FILL      = PatternFill("solid", fgColor="DAEEF3")   # 東急建設（N1ベンチマーク・ライトブルー）
OK_FILL      = PatternFill("solid", fgColor="E2EFDA")   # ◎ 年休+月給両方あり（ライトグリーン）
PARTIAL_FILL = PatternFill("solid", fgColor="FFF2CC")   # △ 片方のみ（ライトイエロー）
NG_FILL      = PatternFill("solid", fgColor="FCE4D6")   # × 両方なし（ライトオレンジ）
NO_FILL      = PatternFill("solid", fgColor="FFFFFF")   # 凡例行（白）

WHITE_FONT  = Font(color="FFFFFF", bold=True)
BLACK_FONT  = Font(color="000000", bold=False)
BOLD_FONT   = Font(color="000000", bold=True)

THIN_BORDER = Border(
    left=Side(style="thin"),
    right=Side(style="thin"),
    top=Side(style="thin"),
    bottom=Side(style="thin"),
)

# サマリー行の背景色（カテゴリ別）
SUMMARY_COLORS = {
    "建築営業":              "DAEEF3",
    "土木営業":              "E2EFDA",
    "建築施工管理":          "FFF2CC",
    "土木施工管理":          "FCE4D6",
    "設備施工管理":          "EBF1DE",
    "再生エネルギー事業開発": "D9E1F2",  # 薄いパープルブルー
    "土木研究開発":          "F2E7D5",  # 薄いタン
    "不動産開発":            "E8D5E8",  # 薄いラベンダー
}


def get_fill(kyujitsu, monthly_l):
    has_kyujitsu = kyujitsu not in (None, "記載なし", "")
    has_salary   = monthly_l not in (None, "記載なし", "")
    if has_kyujitsu and has_salary:
        return OK_FILL, "◎"
    elif has_kyujitsu or has_salary:
        return PARTIAL_FILL, "△"
    else:
        return NG_FILL, "×"


def style_cell(cell, fill=None, font=None, align=None, border=THIN_BORDER):
    if fill:   cell.fill = fill
    if font:   cell.font = font
    if align:  cell.alignment = align
    if border: cell.border = border


def write_sheet(wb, sheet_name, title, companies):
    """
    各カテゴリのシートを作成
    companies: list of dicts with keys:
        企業名, 求人名, 規模感, 年間休日, 残業時間, 月給下限, 月給上限, 給与サマリ, 選定理由, データソース
        is_n1: True なら DAEEF3 固定
    """
    ws = wb.create_sheet(sheet_name)

    # 列幅設定
    col_widths = [16, 34, 26, 10, 16, 12, 12, 44, 38, 26]
    headers = ["企業名", "求人名", "規模感", "年間休日", "残業時間\n（月）",
               "月給下限", "月給上限", "給与サマリ", "選定理由", "データソース"]

    for i, w in enumerate(col_widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.column_dimensions["K"].width = 4  # 空白列

    # --- Row 1: タイトル ---
    ws.row_dimensions[1].height = 24
    ws.merge_cells("A1:K1")
    c = ws["A1"]
    c.value = title
    style_cell(c, fill=NAVY_FILL, font=WHITE_FONT,
               align=Alignment(horizontal="left", vertical="center", wrap_text=False))

    # --- Row 2: ヘッダー ---
    ws.row_dimensions[2].height = 32
    for col_idx, h in enumerate(headers, 1):
        c = ws.cell(row=2, column=col_idx, value=h)
        style_cell(c, fill=HEADER_FILL, font=WHITE_FONT,
                   align=Alignment(horizontal="center", vertical="center", wrap_text=True))

    # --- データ行 ---
    for row_offset, co in enumerate(companies):
        row = 3 + row_offset
        ws.row_dimensions[row].height = 50

        kyujitsu = co.get("年間休日")
        monthly_l = co.get("月給下限")
        is_n1 = co.get("is_n1", False)

        if is_n1:
            row_fill = N1_FILL
        else:
            row_fill, _ = get_fill(kyujitsu, monthly_l)

        values = [
            co.get("企業名", ""),
            co.get("求人名", ""),
            co.get("規模感", ""),
            kyujitsu if kyujitsu else "記載なし",
            co.get("残業時間", "記載なし"),
            monthly_l if monthly_l else "記載なし",
            co.get("月給上限", "記載なし"),
            co.get("給与サマリ", ""),
            co.get("選定理由", ""),
            co.get("データソース", ""),
        ]

        for col_idx, val in enumerate(values, 1):
            c = ws.cell(row=row, column=col_idx, value=val)
            style_cell(c, fill=row_fill, font=BLACK_FONT,
                       align=Alignment(horizontal="left", vertical="center", wrap_text=True))

    # --- 凡例行 ---
    legend_row = 3 + len(companies) + 1
    ws.row_dimensions[legend_row].height = 18
    legend = [("凡例：", None), ("◎ 完備（年間休日+月給）", OK_FILL),
              ("△ 片方のみ", PARTIAL_FILL), ("× 両方なし", NG_FILL)]
    for col_idx, (txt, fill) in enumerate(legend, 1):
        c = ws.cell(row=legend_row, column=col_idx, value=txt)
        c.font = Font(color="000000", bold=True, size=9)
        c.alignment = Alignment(horizontal="left", vertical="center")
        if fill:
            c.fill = fill
        c.border = THIN_BORDER


def write_summary(wb, all_categories):
    """
    選定一覧サマリーシートを作成
    all_categories: list of (category_name, [company_dicts])
    """
    ws = wb.create_sheet("選定一覧サマリー")

    col_widths = [22, 16, 22, 10, 16, 12, 12, 44, 38, 26]
    headers = ["職種カテゴリ", "企業名", "売上規模", "年間休日", "残業時間\n（月）",
               "月給下限", "月給上限", "給与サマリ（抜粋）", "選定理由（抜粋）", "ソース"]

    for i, w in enumerate(col_widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    # --- Row 1: タイトル ---
    ws.row_dimensions[1].height = 24
    ws.merge_cells("A1:J1")
    c = ws["A1"]
    c.value = "競合選定一覧｜佐藤工業 直接競合 全職種"
    style_cell(c, fill=NAVY_FILL, font=WHITE_FONT,
               align=Alignment(horizontal="left", vertical="center"))

    # --- Row 2: ヘッダー ---
    ws.row_dimensions[2].height = 32
    for col_idx, h in enumerate(headers, 1):
        c = ws.cell(row=2, column=col_idx, value=h)
        style_cell(c, fill=HEADER_FILL, font=WHITE_FONT,
                   align=Alignment(horizontal="center", vertical="center", wrap_text=True))

    current_row = 3
    for cat_name, companies in all_categories:
        cat_fill = PatternFill("solid", fgColor=SUMMARY_COLORS.get(cat_name, "EEEEEE"))

        for i, co in enumerate(companies):
            ws.row_dimensions[current_row].height = 50

            kyujitsu = co.get("年間休日")
            monthly_l = co.get("月給下限")

            kyujitsu_val = kyujitsu if kyujitsu else "記載なし"
            monthly_val  = monthly_l if monthly_l else "記載なし"

            values = [
                cat_name if i == 0 else None,
                co.get("企業名", ""),
                co.get("規模感", ""),
                kyujitsu_val,
                co.get("残業時間", "記載なし"),
                monthly_val,
                co.get("月給上限", "記載なし"),
                co.get("給与サマリ", "")[:60] + ("..." if len(str(co.get("給与サマリ", ""))) > 60 else ""),
                co.get("選定理由", "")[:60] + ("..." if len(str(co.get("選定理由", ""))) > 60 else ""),
                co.get("データソース", ""),
            ]

            for col_idx, val in enumerate(values, 1):
                c = ws.cell(row=current_row, column=col_idx, value=val)
                style_cell(c, fill=cat_fill, font=BLACK_FONT,
                           align=Alignment(horizontal="left", vertical="center", wrap_text=True))
            current_row += 1

        # 区切り空白行
        current_row += 1

    # 凡例
    ws.row_dimensions[current_row].height = 18
    legends = [("凡例：", None), ("◎ 完備（年間休日+月給）", OK_FILL),
               ("△ 片方のみ", PARTIAL_FILL), ("× 両方なし", NG_FILL)]
    for col_idx, (txt, fill) in enumerate(legends, 1):
        c = ws.cell(row=current_row, column=col_idx, value=txt)
        c.font = Font(color="000000", bold=True, size=9)
        c.alignment = Alignment(horizontal="left", vertical="center")
        if fill:
            c.fill = fill
        c.border = THIN_BORDER


# ==============================================================================
# データ定義
# ==============================================================================

# ------ 建築営業 ------
建築営業_data = [
    dict(
        is_n1=True,
        企業名="東急建設",
        求人名="建築営業｜法人顧客への提案・プロジェクト推進（総合職）",
        規模感="売上約1,900億円 / 東証プライム上場",
        年間休日=None,
        残業時間="実残業記載なし（年収例は残業20h想定）",
        月給下限=300000,
        月給上限=455000,
        給与サマリ="28歳716万円、30歳761万円、35歳869万円、40歳1,026万円（大卒モデル）",
        選定理由="規模・給与帯ともに最も近い準大手。N1分析済。月給30-45.5万の実数値あり。",
        データソース="N1ファイル（一次情報）",
    ),
    dict(
        企業名="東亜建設工業",
        求人名="建築営業（民間工事請負営業）",
        規模感="売上約1,300億円 / 東証プライム / 海洋土木に強み",
        年間休日=123,
        残業時間="約30h（doda求人より）",
        月給下限=280000,
        月給上限=380000,
        給与サマリ="月給280,000円～380,000円 / 年間休日124日 / 賞与6.06ヶ月実績",
        選定理由="売上規模・月給帯が佐藤工業に最も近い中堅ゼネコン。年間休日・月給両方完備。",
        データソース="外部調査（doda/東亜建設工業）",
    ),
    dict(
        企業名="名工建設",
        求人名="建築営業（官公庁・民間建築受注）",
        規模感="売上約1,000億円 / 名古屋証券取引所 / 中部地方の中堅ゼネコン",
        年間休日=121,
        残業時間="約24h（doda求人より）",
        月給下限=300000,
        月給上限=500000,
        給与サマリ="月給300,000円～500,000円 / 年収500万～900万円 / 官公庁・民間建築受注営業",
        選定理由="中部〜北陸エリアで重なる地方中堅ゼネコン。残業24hと低く、年間休日・月給完備。",
        データソース="外部調査（meikokensetsu-recruit.com / doda）",
    ),
]

# ------ 土木営業 ------
土木営業_data = [
    dict(
        is_n1=True,
        企業名="東急建設",
        求人名="土木営業｜総合職",
        規模感="売上約1,900億円 / 東証プライム上場",
        年間休日=None,
        残業時間="実残業記載なし（年収例は残業20h想定）",
        月給下限=300000,
        月給上限=455000,
        給与サマリ="28歳716万円、30歳761万円、35歳869万円、40歳1,026万円（大卒モデル）",
        選定理由="N1分析済み。土木営業で月給・モデル年収の実数値あり。規模・給与帯ともに競合として妥当。",
        データソース="N1ファイル（一次情報）",
    ),
    dict(
        企業名="名工建設",
        求人名="土木営業（官公庁・土木工事受注）",
        規模感="売上約1,000億円 / 中部地方の中堅ゼネコン",
        年間休日=121,
        残業時間="約24h（doda求人より）",
        月給下限=300000,
        月給上限=500000,
        給与サマリ="月給300,000円～500,000円 / 官公庁（県庁・役所）訪問、土木工事計画情報収集・受注",
        選定理由="土木営業で年間休日・月給両方完備の数少ない中堅ゼネコン。地域的重複あり。",
        データソース="外部調査（meikokensetsu-recruit.com / doda）",
    ),
]

# ------ 建築施工管理 ------
建築施工管理_data = [
    dict(
        is_n1=True,
        企業名="東急建設",
        求人名="建築施工技術者（総合職）",
        規模感="売上約1,900億円 / 東証プライム",
        年間休日=127,
        残業時間="記載なし",
        月給下限=240000,
        月給上限=None,
        給与サマリ="月給240,000円～ / 給与応相談（経験・能力により）",
        選定理由="N1分析済みの最有力競合。年間休日127日・月給下限24万の実数値あり。",
        データソース="File3（一次情報補完済）",
    ),
    dict(
        企業名="三井住友建設",
        求人名="建築施工技術者（全国型）",
        規模感="売上約3,600億円 / 東証プライム",
        年間休日=127,
        残業時間=20,
        月給下限=None,
        月給上限=None,
        給与サマリ="[モデル月収]（全国社員・外勤）30歳：約380,000円 / 残業20h / 年間休日127日",
        選定理由="年間休日127日と残業20hの数値完備。モデル月収情報あり（30歳38万円台）。規模はやや大きいが給与帯が近い。",
        データソース="File3（一次情報）",
    ),
    dict(
        企業名="南海辰村建設",
        求人名="建築・土木施工管理（総合職）",
        規模感="売上約700億円 / 大阪拠点の中堅ゼネコン",
        年間休日=120,
        残業時間=30,
        月給下限=240000,
        月給上限=None,
        給与サマリ="【技術系（総合職）】月給240,000円～ / 賞与年2回 / 年間休日120日",
        選定理由="月給下限24万・年間休日120日・残業30hすべて実数値あり。中堅規模で直接競合。",
        データソース="File3（一次情報補完済）",
    ),
]

# ------ 土木施工管理 ------
土木施工管理_data = [
    dict(
        is_n1=True,
        企業名="東急建設",
        求人名="土木施工技術者（総合職）",
        規模感="売上約1,900億円 / 東証プライム",
        年間休日=127,
        残業時間="記載なし",
        月給下限=240000,
        月給上限=None,
        給与サマリ="月給240,000円～ / 給与応相談（経験・能力により）",
        選定理由="N1分析済みの最有力競合。年間休日127日・月給下限24万あり。",
        データソース="File3（一次情報補完済）",
    ),
    dict(
        企業名="西松建設",
        求人名="土木施工技術者（総合職）",
        規模感="売上約1,700億円 / 東証プライム / 佐藤工業と最も規模が近い準大手",
        年間休日=120,
        残業時間=30,
        月給下限=None,
        月給上限=None,
        給与サマリ="モデル年収（残業45h込）：総合職30歳：約590万円、35歳：約720万円 / 年間休日120日",
        選定理由="売上規模が佐藤工業に最も近い（1,700億円）。モデル年収の実数値（30歳590万）あり。",
        データソース="File3（一次情報）",
    ),
    dict(
        企業名="TSUCHIYA",
        求人名="土木施工技術者（総合職）",
        規模感="売上約500億円 / 東証スタンダード / 中部地方の中堅ゼネコン",
        年間休日=125,
        残業時間=36,
        月給下限=250000,
        月給上限=None,
        給与サマリ="月給250,000円～（資格・経験による） / 年間休日125日 / 残業36h",
        選定理由="月給下限25万・年間休日125日・残業36hすべて実数値あり。北陸・中部エリアで競合。",
        データソース="File3（一次情報補完済）",
    ),
]

# ------ 設備施工管理 ------
設備施工管理_data = [
    dict(
        is_n1=True,
        企業名="東急建設",
        求人名="建築設備施工技術者（総合職）",
        規模感="売上約1,900億円 / 東証プライム",
        年間休日=127,
        残業時間="記載なし",
        月給下限=240000,
        月給上限=None,
        給与サマリ="月給240,000円～ / 固定残業手当（30h分）100,000円別途支給",
        選定理由="N1分析済み。月給下限・年間休日ともに実数値あり。設備部門を抱えるゼネコン筆頭競合。",
        データソース="File3（一次情報補完済）",
    ),
    dict(
        企業名="南海辰村建設",
        求人名="建築設備・土木施工管理（総合職）",
        規模感="売上約700億円 / 中堅ゼネコン",
        年間休日=120,
        残業時間=30,
        月給下限=240000,
        月給上限=None,
        給与サマリ="月給240,000円～ / 建築設備・土木・軌道・鉄道電気設備工事の施工管理",
        選定理由="月給下限・年間休日・残業すべて実数値あり。設備施工管理で候補者を奪い合う規模の中堅。",
        データソース="File3（一次情報補完済）",
    ),
    dict(
        企業名="朝日工業社",
        求人名="設備施工管理（空調・衛生設備）",
        規模感="売上約900億円 / 設備専業の中堅",
        年間休日=120,
        残業時間="記載なし",
        月給下限=None,
        月給上限=None,
        給与サマリ="モデル年収：30歳780万円 / 40歳980万円（賞与6ヶ月含む）",
        選定理由="設備専業の競合。モデル年収（30歳780万）という具体的な比較指標あり。設備施工管理候補者の流出先として要注視。",
        データソース="File3（一次情報）",
    ),
]

# ------ 再生エネルギー事業開発（新規） ------
再生エネ_data = [
    dict(
        企業名="清水建設",
        求人名="グリーンエネルギー事業本部｜再生可能エネルギー発電所 事業開発・推進",
        規模感="売上約1.6兆円 / スーパーゼネコン / 東証プライム",
        年間休日=122,
        残業時間="10〜20h（hrmos掲載求人より）",
        月給下限=286000,
        月給上限=None,
        給与サマリ="月額基本給286,000円〜 / 予定年収600〜1,300万円 / 太陽光・バイオマス等の発電施設開発",
        選定理由="スーパーゼネコン比較軸。hrmos掲載で年休122日・月給基本給28.6万以上を確認。年収レンジ最大1,300万。",
        データソース="hrmos.co（清水建設）/ doda",
    ),
    dict(
        企業名="前田建設工業",
        求人名="再生可能エネルギー事業開発（インフロニア・ホールディングス グループ）",
        規模感="売上約5,200億円 / インフロニアHD傘下 / 東証プライム",
        年間休日=124,
        残業時間="21h（doda求人より）",
        月給下限=None,
        月給上限=None,
        給与サマリ="モデル年収：35歳800万・40歳880万（賞与・残業込）/ 国内最大級の再エネポートフォリオ保有",
        選定理由="脱請負型の再エネ先進企業。年休124日・残業21hを確認。月給は非公開だがモデル年収レンジあり。",
        データソース="doda / 採用サイト",
    ),
    dict(
        企業名="大成建設",
        求人名="エネルギー事業開発（大成建設 キャリア採用）",
        規模感="売上約2.0兆円 / スーパーゼネコン / 東証プライム",
        年間休日=125,
        残業時間="記載なし",
        月給下限=None,
        月給上限=None,
        給与サマリ="平均年収1,058万（全社平均・42.4歳） / エネルギー供給・地域開発事業を展開 / 月給制",
        選定理由="スーパーゼネコン比較軸。年休125日確認済み。月給・残業は記載なし。",
        データソース="採用サイト / 公式情報",
    ),
]

# ------ 土木研究開発（新規） ------
土木研究_data = [
    dict(
        企業名="大林組",
        求人名="技術研究所｜土木系研究員（コンクリート・地盤・構造・DX研究）",
        規模感="売上約2.2兆円 / スーパーゼネコン / 東証プライム",
        年間休日=125,
        残業時間="20〜30h（doda求人より）",
        月給下限=280000,
        月給上限=380000,
        給与サマリ="月給280,000〜380,000円 / 年収690〜1,300万（同社doda求人実績） / 技術研究所（東京・清瀬）",
        選定理由="年休125日・月給28〜38万の実数値両方確認済み（◎）。スーパーゼネコン中で最も詳細データが揃う。",
        データソース="doda（前セッション調査）",
    ),
    dict(
        is_n1=True,
        企業名="東急建設",
        求人名="研究開発（建築・土木構造）｜耐震・構造解析技術の研究開発",
        規模感="売上約1,900億円 / 準大手ゼネコン / 東証プライム",
        年間休日=None,
        残業時間="記載なし",
        月給下限=300000,
        月給上限=455000,
        給与サマリ="キャリア職：月給300,000〜455,000円 / 賞与年2回（7月・12月） / 住宅手当15,000〜45,000円（40歳以下）",
        選定理由="N1分析済。hrmos掲載で月給30〜45.5万の実数値あり。準大手ゼネコンとして規模・給与帯が競合に近い。",
        データソース="hrmos.co（東急建設）",
    ),
    dict(
        企業名="鹿島建設",
        求人名="技術研究所｜土木系研究職（コンクリート材料・土質地盤・岩盤・土木構造）",
        規模感="売上約2.1兆円 / スーパーゼネコン / 東証プライム",
        年間休日=None,
        残業時間="34.7h（全社平均・採用サイト記載）",
        月給下限=None,
        月給上限=None,
        給与サマリ="平均年収1,185万（全社平均） / 土木・コンクリート材料・地盤研究で国内最高水準",
        選定理由="土木研究開発の最高水準競合。月給・年休の公開情報なし（×）だが採用難易度・技術競合として重要。",
        データソース="採用サイト / doda",
    ),
]

# ------ 不動産開発（新規） ------
不動産開発_data = [
    dict(
        企業名="鹿島建設",
        求人名="不動産開発部｜開発事業企画・用地取得・販売（一気通貫型）",
        規模感="売上約2.1兆円 / スーパーゼネコン / 東証プライム",
        年間休日=125,
        残業時間="20h（固定残業として求人明示）",
        月給下限=280000,
        月給上限=800000,
        給与サマリ="月給280,000〜800,000円（固定残業20h分38,000円含）/ 年休126日 / 中途比率61.4%",
        選定理由="年休125日・月給28〜80万の実数値両方確認済み（◎）。一気通貫型の開発職として最も詳細データが揃う。",
        データソース="doda / 採用サイト",
    ),
    dict(
        企業名="大成建設",
        求人名="不動産事業開発（大成建設 キャリア採用）",
        規模感="売上約2.0兆円 / スーパーゼネコン / 東証プライム",
        年間休日=125,
        残業時間="記載なし",
        月給下限=None,
        月給上限=None,
        給与サマリ="平均年収1,058万（全社平均・42.4歳） / 年間休日125日 / 土日祝休み",
        選定理由="スーパーゼネコン比較軸。年休125日確認済み。月給・残業は非公開。",
        データソース="採用サイト / 公式情報",
    ),
    dict(
        企業名="西松建設",
        求人名="不動産開発・アクイジション・管理運営職",
        規模感="売上約1,700億円 / 東証プライム / 土木・不動産両輪経営",
        年間休日=None,
        残業時間="45h想定（モデル年収計算基準）",
        月給下限=None,
        月給上限=None,
        給与サマリ="モデル年収（残業月45h込）で設定。具体的月給は非公開 / 宅地建物取引士等資格者歓迎",
        選定理由="不動産開発・アクイジション職を明示掲載する数少ないゼネコン。月給・年休は記載なし（×）。",
        データソース="西松建設 採用サイト",
    ),
]


# ==============================================================================
# Excelファイル作成
# ==============================================================================

wb = openpyxl.Workbook()
wb.remove(wb.active)  # デフォルトシート削除

# サマリーを先に定義（最初のシートにするため後で作成）
all_categories = [
    ("建築営業",             建築営業_data),
    ("土木営業",             土木営業_data),
    ("建築施工管理",         建築施工管理_data),
    ("土木施工管理",         土木施工管理_data),
    ("設備施工管理",         設備施工管理_data),
    ("再生エネルギー事業開発", 再生エネ_data),
    ("土木研究開発",         土木研究_data),
    ("不動産開発",           不動産開発_data),
]

# サマリーシートを最初に作成
write_summary(wb, all_categories)

# 各カテゴリシートを作成
sheet_configs = [
    ("建築営業",             "競合求人比較｜建築営業（佐藤工業 vs 競合3社）",              建築営業_data),
    ("土木営業",             "競合求人比較｜土木営業（佐藤工業 vs 競合2社）",              土木営業_data),
    ("建築施工管理",         "競合求人比較｜建築施工管理（佐藤工業 vs 競合3社）",          建築施工管理_data),
    ("土木施工管理",         "競合求人比較｜土木施工管理（佐藤工業 vs 競合3社）",          土木施工管理_data),
    ("設備施工管理",         "競合求人比較｜設備施工管理（佐藤工業 vs 競合3社）",          設備施工管理_data),
    ("再生エネルギー事業開発", "競合求人比較｜再生エネルギー事業開発（佐藤工業 vs 競合3社）", 再生エネ_data),
    ("土木研究開発",         "競合求人比較｜土木研究開発（佐藤工業 vs 競合3社）",          土木研究_data),
    ("不動産開発",           "競合求人比較｜不動産開発（佐藤工業 vs 競合3社）",            不動産開発_data),
]

for sheet_name, title, data in sheet_configs:
    write_sheet(wb, sheet_name, title, data)

output_path = "/tmp/競合求人_選定比較_v2.xlsx"
wb.save(output_path)
print(f"✅ 保存完了: {output_path}")
print(f"   シート数: {len(wb.sheetnames)}")
for sn in wb.sheetnames:
    print(f"   - {sn}")
