import pandas as pd
import re

INPUT_XLSX  = "input.xlsx"   # ← ここを変更
INPUT_SHEET = 0              # シート番号 or シート名（0 = 先頭）
OUTPUT_XLSX = "output.xlsx"  # ← ここを変更

COLUMN_MAP = {
    'タイプ':     ['タイプ', '雇用形態', '雇用タイプ'],
    '名前':       ['名前', '企業名', '会社名'],
    'タイトル':   ['タイトル', '職種', '求人タイトル'],
    '給与':       ['給与', '給与タイプ', '給与形態'],
    '給与2':      ['給与2', '給与額', '給与レンジ'],
    '場所':       ['場所', '勤務地', '所在地'],
    'キーワード': ['キーワード', 'タグ', '条件'],
    'コンテンツ': ['コンテンツ', '仕事内容', '業務内容'],
    'コンテンツ5':['コンテンツ5', '必須要件', '応募要件'],
}

def normalize_columns(df):
    rename = {}
    for canonical, variants in COLUMN_MAP.items():
        for col in df.columns:
            if col.strip() in variants:
                rename[col] = canonical
                break
    return df.rename(columns=rename)

def _parse_man_en(s):
    s = s.strip()
    m = re.match(r'(\d+)万(\d+)円', s)
    if m:
        return (int(m.group(1)) * 10000 + int(m.group(2))) / 10000
    m = re.match(r'(\d+(?:\.\d+)?)万円?', s)
    return float(m.group(1)) if m else None

def parse_lower_annual(kyuyo_type, kyuyo_amount):
    if pd.isna(kyuyo_type) or pd.isna(kyuyo_amount):
        return None
    t = str(kyuyo_type).strip()
    a = str(kyuyo_amount).strip()
    lower_str = a.split('～')[0] if '～' in a else a.replace('以上', '')
    lower_man = _parse_man_en(lower_str)
    if lower_man is None:
        return None
    if '月給' in t:
        return round(lower_man * 15)
    elif '年俸' in t:
        return round(lower_man)
    return None

def extract_nenkyu(row):
    kw = str(row.get('キーワード') or '')
    m = re.search(r'年間休日(\d+)日', kw)
    if m:
        return int(m.group(1))
    for col in ('コンテンツ5', 'コンテンツ'):
        m = re.search(r'年(?:間)?休(?:日)?(\d+)日', str(row.get(col) or ''))
        if m:
            return int(m.group(1))
    return None

def extract_zangyo(row):
    kw = str(row.get('キーワード') or '')
    m = re.search(r'月平均残業時間(\d+)時間以内', kw)
    if m:
        return int(m.group(1))
    for col in ('コンテンツ5', 'コンテンツ'):
        text = str(row.get(col) or '')
        m = re.search(r'残業月?(\d+)h', text)
        if m:
            return int(m.group(1))
        m = re.search(r'(?:月平均)?残業(?:時間)?月?(\d+)時間(?!以上)', text)
        if m:
            return int(m.group(1))
    return None

def extract_hissu(content5):
    if pd.isna(content5):
        return None
    text = str(content5)
    m = re.search(r'【[^】]*必須[^】]*】(.+?)(?=【|$)', text, re.DOTALL)
    if m:
        return m.group(1).strip()
    m = re.search(r'\[必須\](.+?)(?=【|\[|$)', text, re.DOTALL)
    if m:
        return m.group(1).strip()
    text = re.sub(r'^必要な経験・能力等\s*', '', text).strip()
    return re.split(r'学歴・資格', text)[0].strip() or None

xl = pd.ExcelFile(INPUT_XLSX)
print(f"シート一覧: {xl.sheet_names}")

all_records = []
for sheet_name in xl.sheet_names:
    df = xl.parse(sheet_name)
    if df.empty:
        continue
    df = normalize_columns(df)
    print(f"  [{sheet_name}] {len(df)}行")
    for _, row in df.iterrows():
        all_records.append({
            '企業名':         row.get('名前'),
            '職種':           row.get('タイトル'),
            '勤務地':         row.get('場所'),
            '下限年収(万円)': parse_lower_annual(row.get('給与'), row.get('給与2')),
            '年間休日':       extract_nenkyu(row),
            '月残業(h)':      extract_zangyo(row),
            '必須要件':       extract_hissu(row.get('コンテンツ5')),
        })

df_out = pd.DataFrame(all_records).T  # 転置（縦横逆）
df_out.to_excel(OUTPUT_XLSX, sheet_name='データ', index=True, header=False, engine='openpyxl')
print(f"\n完了: {len(all_records)}件 → {OUTPUT_XLSX}")
