"""
CSV → Excel 変換スクリプト
対象: r-agentの求人CSVデータ
出力: 建築営業_市場調査 / サマリー の2シート構成
"""

import pandas as pd
import re

# ── 設定 ──────────────────────────────────────────────────────────────────────

INPUT_CSV   = "input.csv"   # 変換元CSVファイルのパス ← ここを変更
OUTPUT_XLSX = "output.xlsx" # 出力先Excelファイルのパス ← ここを変更
ENCODING    = "utf-8"       # 文字化けする場合は "shift_jis" や "cp932" に変更

# ── 給与パース ────────────────────────────────────────────────────────────────

def _parse_man_en(s: str) -> float | None:
    """'X万Y円' / 'X万円' を万円単位の float に変換"""
    s = s.strip()
    m = re.match(r'(\d+)万(\d+)円', s)
    if m:
        return (int(m.group(1)) * 10000 + int(m.group(2))) / 10000
    m = re.match(r'(\d+(?:\.\d+)?)万円?', s)
    if m:
        return float(m.group(1))
    return None

def parse_salary(kyuyo_type, kyuyo_amount):
    """
    (給与タイプ, 給与額文字列) → (換算方法, 年収下限万円, 年収上限万円)

    月給 × 14（12ヶ月 + 賞与2ヶ月想定）で年収換算
    年俸はそのまま使用
    """
    if pd.isna(kyuyo_type) or pd.isna(kyuyo_amount):
        return None, None, None

    kyuyo_type   = str(kyuyo_type).strip()
    kyuyo_amount = str(kyuyo_amount).strip()

    if '～' in kyuyo_amount:
        lower_str, upper_str = kyuyo_amount.split('～', 1)
        lower_man = _parse_man_en(lower_str)
        upper_man = _parse_man_en(upper_str)
    elif '以上' in kyuyo_amount:
        lower_man = _parse_man_en(kyuyo_amount.replace('以上', ''))
        upper_man = None
    else:
        lower_man = _parse_man_en(kyuyo_amount)
        upper_man = lower_man

    if '月給' in kyuyo_type:
        method, mult = '月給×14', 14
    elif '年俸' in kyuyo_type:
        method, mult = '年俸そのまま', 1
    else:
        method, mult = kyuyo_type, 1

    annual_lower = round(lower_man * mult) if lower_man is not None else None
    annual_upper = round(upper_man * mult) if upper_man is not None else None
    return method, annual_lower, annual_upper

# ── 年間休日・残業の抽出 ───────────────────────────────────────────────────────

def extract_nenkyu(row) -> int | None:
    """年間休日日数を抽出（キーワード → コンテンツ5 → コンテンツ の優先順）"""
    # キーワードタグ: "年間休日120日以上"
    kw = str(row.get('キーワード') or '')
    m = re.search(r'年間休日(\d+)日', kw)
    if m:
        return int(m.group(1))
    # 本文: "年間休日125日" / "年休123日" など
    for col in ('コンテンツ5', 'コンテンツ'):
        text = str(row.get(col) or '')
        m = re.search(r'年(?:間)?休(?:日)?(\d+)日', text)
        if m:
            return int(m.group(1))
    return None

def extract_zangyo(row) -> int | None:
    """月残業時間を抽出（キーワード → コンテンツ5 → コンテンツ の優先順）"""
    # キーワードタグ: "月平均残業時間20時間以内"
    kw = str(row.get('キーワード') or '')
    m = re.search(r'月平均残業時間(\d+)時間以内', kw)
    if m:
        return int(m.group(1))
    # 本文: "残業月20h" / "残業20時間" / "月18h" など
    for col in ('コンテンツ5', 'コンテンツ'):
        text = str(row.get(col) or '')
        m = re.search(r'残業月?(\d+)h', text)
        if m:
            return int(m.group(1))
        m = re.search(r'(?:月平均)?残業(?:時間)?月?(\d+)時間(?!以上)', text)
        if m:
            return int(m.group(1))
    return None

# ── 必須要件の抽出 ─────────────────────────────────────────────────────────────

def extract_hissu(content5) -> str | None:
    """
    コンテンツ5 から必須要件を抽出

    【〇〇必須】タグがある場合 → その内容を取得
    ない場合 → 「必要な経験・能力等」プレフィックスを除いた全文
    """
    if pd.isna(content5):
        return None
    text = str(content5)

    # 【〇〇必須】タグ（バリエーション全対応）
    m = re.search(r'【[^】]*必須[^】]*】(.+?)(?=【|$)', text, re.DOTALL)
    if m:
        return m.group(1).strip()

    # 角括弧パターン: [必須]
    m = re.search(r'\[必須\](.+?)(?=【|\[|$)', text, re.DOTALL)
    if m:
        return m.group(1).strip()

    # 【必須】なし → プレフィックスを除いた全文
    text = re.sub(r'^必要な経験・能力等\s*', '', text).strip()
    # 「学歴・資格」以降は除外
    text = re.split(r'学歴・資格', text)[0].strip()
    return text if text else None

# ── 条件タグの整形 ─────────────────────────────────────────────────────────────

def format_tags(keywords) -> str | None:
    """改行区切りのキーワードをカンマ区切りに変換"""
    if pd.isna(keywords):
        return None
    tags = [t.strip() for t in str(keywords).split('\n') if t.strip()]
    return ', '.join(tags)

# ── メイン処理 ────────────────────────────────────────────────────────────────

df = pd.read_csv(INPUT_CSV, encoding=ENCODING, engine='python')

records = []
for _, row in df.iterrows():
    method, lower, upper = parse_salary(row.get('給与'), row.get('給与2'))
    kyuyo_str = f"{str(row.get('給与') or '').strip()} {str(row.get('給与2') or '').strip()}".strip()

    records.append({
        '企業名':         row.get('名前'),
        '職種':           row.get('タイトル'),
        '勤務地':         row.get('場所'),
        '雇用形態':       row.get('タイプ'),
        '給与表記':       kyuyo_str,
        '年収下限(万円)': lower,
        '年収上限(万円)': upper,
        '換算方法':       method,
        '年間休日':       extract_nenkyu(row),
        '残業(月h)':      extract_zangyo(row),
        '必須要件':       extract_hissu(row.get('コンテンツ5')),
        '条件タグ':       format_tags(row.get('キーワード')),
    })

df_out = pd.DataFrame(records)

# ── サマリー集計 ──────────────────────────────────────────────────────────────

total      = len(df_out)
unique_co  = df_out['企業名'].nunique()
lower_med  = round(df_out['年収下限(万円)'].median())
lower_avg  = round(df_out['年収下限(万円)'].mean(), 1)
upper_med  = round(df_out['年収上限(万円)'].median())
upper_avg  = round(df_out['年収上限(万円)'].mean(), 1)
nenkyu_n   = int(df_out['年間休日'].notna().sum())
nenkyu_med = int(df_out['年間休日'].median())
zangyo_n   = int(df_out['残業(月h)'].notna().sum())
zangyo_med = int(df_out['残業(月h)'].median())
hissu_n    = int(df_out['必須要件'].notna().sum())

summary_rows = [
    ('建築営業×一都三県 市場調査データ',       None),
    ('※月給表記は×14（賞与2ヶ月想定）で年収換算', None),
    (None, None),
    ('総求人数',       total),
    ('ユニーク企業数', unique_co),
    (None, None),
    ('【年収（万円）】', None),
    ('年収下限 中央値', lower_med),
    ('年収下限 平均',   lower_avg),
    ('年収上限 中央値', upper_med),
    ('年収上限 平均',   upper_avg),
    (None, None),
    ('【年間休日】', None),
    ('記載あり', f'{nenkyu_n}件'),
    ('中央値',   nenkyu_med),
    (None, None),
    ('【残業】', None),
    ('記載あり', f'{zangyo_n}件'),
    ('中央値',   zangyo_med),
    (None, None),
    ('【必須要件】', None),
    ('記載あり', f'{hissu_n}件 ({hissu_n / total * 100:.0f}%)'),
]

# ── Excel 書き出し ──────────────────────────────────────────────────────────

with pd.ExcelWriter(OUTPUT_XLSX, engine='openpyxl') as writer:
    df_out.to_excel(writer, sheet_name='建築営業_市場調査', index=False)
    ws2 = writer.book.create_sheet('サマリー')
    for row_data in summary_rows:
        ws2.append(list(row_data))

print(f"完了: {total} 件 → {OUTPUT_XLSX}")
print(f"  年収下限 中央値: {lower_med}万 / 平均: {lower_avg}万")
print(f"  年収上限 中央値: {upper_med}万 / 平均: {upper_avg}万")
print(f"  年間休日 記載: {nenkyu_n}件 (中央値 {nenkyu_med}日)")
print(f"  残業    記載: {zangyo_n}件 (中央値 {zangyo_med}h)")
print(f"  必須要件 記載: {hissu_n}件 ({hissu_n / total * 100:.0f}%)")
