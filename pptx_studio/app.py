"""
パワポスタジオ — デザインシステム搭載のPowerPointビルダー
非エンジニアがプロ品質のスライドをノーコードで作れる Streamlit アプリ

起動: streamlit run app.py
"""
import streamlit as st
from builder import build_pptx, SLIDE_TYPES, SLIDE_FIELDS
from ds import THEMES

st.set_page_config(
    page_title="パワポスタジオ",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ─────────────────────────────────────────────────
st.markdown("""
<style>
/* Sidebar dark theme */
[data-testid="stSidebar"] > div:first-child {
    background: #1F2937;
}
[data-testid="stSidebar"] h1,[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,[data-testid="stSidebar"] p,
[data-testid="stSidebar"] label,[data-testid="stSidebar"] span,
[data-testid="stSidebar"] .stRadio label {
    color: #F9FAFB !important;
}
[data-testid="stSidebar"] .stCaption { color: #9CA3AF !important; }
[data-testid="stSidebar"] .stTextInput input {
    background: #374151 !important;
    color: #F9FAFB !important;
    border-color: #4B5563 !important;
}
/* Hide Streamlit branding */
#MainMenu, footer { visibility: hidden; }
/* Slide list buttons */
.stButton > button[kind="secondary"] {
    background: #F9FAFB;
    border: 1px solid #E5E7EB;
    color: #374151;
    font-size: 13px;
    text-align: left;
    justify-content: flex-start;
}
.stButton > button[kind="primary"] {
    font-size: 13px;
    text-align: left;
    justify-content: flex-start;
}
/* Editor area */
div[data-testid="stVerticalBlock"] hr {
    margin: 12px 0;
}
</style>
""", unsafe_allow_html=True)

# ── Helpers ────────────────────────────────────────────────────

def _defaults(type_key: str) -> dict:
    d = {f["key"]: f["default"] for f in SLIDE_FIELDS.get(type_key, [])}
    d["type"] = type_key
    return d

def _clear_form_state():
    for k in list(st.session_state.keys()):
        if k.startswith("f_"):
            del st.session_state[k]

def _on_change(slide_idx: int, field_key: str):
    wk = f"f_{slide_idx}_{field_key}"
    if wk in st.session_state:
        st.session_state.slides[slide_idx][field_key] = st.session_state[wk]

# ── Session state init ─────────────────────────────────────────

if "slides" not in st.session_state:
    st.session_state.slides = [
        {**_defaults("title"),
         "title": "プレゼンテーションタイトル",
         "subtitle": "サブタイトル",
         "date": "2024年",
         "author": ""},
        {**_defaults("section"),
         "section_number": "01",
         "section_title": "第一章：課題と背景"},
        {**_defaults("kpi3"),
         "slide_title": "主要KPI",
         "kpi1_label": "売上高", "kpi1_value": "¥120M", "kpi1_unit": "前年比 +20%",
         "kpi2_label": "顧客数", "kpi2_value": "1,580", "kpi2_unit": "前年比 +350件",
         "kpi3_label": "NPS",   "kpi3_value": "72",    "kpi3_unit": "業界平均 +18pt"},
        {**_defaults("bullet"),
         "slide_title": "ポイントまとめ",
         "bullets": "市場規模は年率8%で成長中\nデジタル化が競合優位の鍵\n人材確保が最大の課題"},
        {**_defaults("chart_bar"),
         "slide_title": "売上推移",
         "chart_title": "年間売上高（百万円）",
         "data_csv": "2020,85\n2021,95\n2022,108\n2023,120\n2024,138"},
        {**_defaults("closing"),
         "main_message": "ありがとうございました"},
    ]

if "sel" not in st.session_state:
    st.session_state.sel = 0
if "theme_key" not in st.session_state:
    st.session_state.theme_key = "navy"
if "company" not in st.session_state:
    st.session_state.company = ""

slides = st.session_state.slides

# ── Sidebar: Design system + Export ───────────────────────────

with st.sidebar:
    st.markdown("## 🎨 デザインシステム")

    # Theme picker
    st.markdown("#### テーマ")
    selected_theme = st.radio(
        "theme",
        options=list(THEMES.keys()),
        format_func=lambda k: f"{THEMES[k].emoji}  {THEMES[k].name}",
        index=list(THEMES.keys()).index(st.session_state.theme_key),
        label_visibility="collapsed",
    )
    st.session_state.theme_key = selected_theme
    theme = THEMES[selected_theme]

    # Color token swatches
    st.markdown("**カラートークン**")
    swatches = [
        ("Primary", theme.colors.primary),
        ("Accent",  theme.colors.accent),
        ("Soft",    theme.colors.accent_soft),
        ("Surface", theme.colors.surface_alt),
    ]
    sw = '<div style="display:flex;gap:8px;margin:6px 0 12px">'
    for name, col in swatches:
        sw += (
            f'<div style="text-align:center">'
            f'<div style="width:36px;height:36px;background:{col};border-radius:6px;'
            f'border:2px solid rgba(255,255,255,0.15)"></div>'
            f'<div style="font-size:8px;color:#9CA3AF;margin-top:3px">{name}</div>'
            f'</div>'
        )
    sw += '</div>'
    st.markdown(sw, unsafe_allow_html=True)

    # Typography info
    with st.expander("タイポグラフィ"):
        st.markdown(f"""
| トークン | サイズ |
|---------|-------|
| 見出し（大） | {theme.typo.sz_huge}pt |
| スライドタイトル | {theme.typo.sz_h1}pt |
| セクション見出し | {theme.typo.sz_h2}pt |
| KPI数値 | {theme.typo.sz_kpi}pt |
| 本文 | {theme.typo.sz_body}pt |
| キャプション | {theme.typo.sz_sm}pt |
        """)

    st.markdown("---")
    st.markdown("#### 会社・組織名")
    st.session_state.company = st.text_input(
        "company_name",
        value=st.session_state.company,
        placeholder="フッターに表示（任意）",
        label_visibility="collapsed",
    )

    st.markdown("---")
    st.markdown(f"#### エクスポート　`{len(slides)} スライド`")

    if st.button("⬇️  PowerPoint を生成", use_container_width=True, type="primary"):
        with st.spinner("スライド生成中…"):
            buf = build_pptx(slides, theme, st.session_state.company)
        st.download_button(
            label="📥  ダウンロード (.pptx)",
            data=buf,
            file_name="presentation.pptx",
            mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            use_container_width=True,
        )

    st.markdown("---")
    st.caption("💡 テキスト入力は自動保存。テーマを変えるだけで全スライドのデザインが変わります。")

# ── Main header ────────────────────────────────────────────────

st.markdown("# 🎨 パワポスタジオ")
st.caption("デザインシステム搭載のPowerPointビルダー — 非エンジニアでもプロ品質のスライドを")
st.markdown("---")

col_list, col_editor = st.columns([1, 2], gap="large")

# ── Left: Slide list ───────────────────────────────────────────

with col_list:
    st.markdown("### スライド一覧")

    for i, sl in enumerate(slides):
        stype = sl.get("type", "bullet")
        info  = SLIDE_TYPES.get(stype, {})
        preview = (
            sl.get("title") or sl.get("slide_title") or
            sl.get("section_title") or sl.get("main_message") or
            sl.get("message") or info.get("label", "")
        )
        preview = (preview or "")[:22]
        is_sel  = (st.session_state.sel == i)

        r1, r2, r3, r4 = st.columns([5, 1, 1, 1])
        with r1:
            label = f"{info.get('icon','📄')}  {i+1}. {preview}"
            if st.button(label, key=f"bsel_{i}",
                         use_container_width=True,
                         type="primary" if is_sel else "secondary"):
                st.session_state.sel = i
                st.rerun()
        with r2:
            if i > 0 and st.button("↑", key=f"bup_{i}", use_container_width=True):
                slides[i], slides[i-1] = slides[i-1], slides[i]
                st.session_state.sel = i - 1
                _clear_form_state()
                st.rerun()
        with r3:
            if i < len(slides)-1 and st.button("↓", key=f"bdn_{i}", use_container_width=True):
                slides[i], slides[i+1] = slides[i+1], slides[i]
                st.session_state.sel = i + 1
                _clear_form_state()
                st.rerun()
        with r4:
            if st.button("🗑", key=f"bdel_{i}", use_container_width=True):
                slides.pop(i)
                st.session_state.sel = max(0, i - 1)
                _clear_form_state()
                st.rerun()

    st.markdown("---")
    st.markdown("**➕ スライドを追加**")

    add_type = st.selectbox(
        "add_type_sel",
        options=list(SLIDE_TYPES.keys()),
        format_func=lambda k: f"{SLIDE_TYPES[k]['icon']}  {SLIDE_TYPES[k]['label']}",
        label_visibility="collapsed",
    )
    st.caption(SLIDE_TYPES[add_type]["desc"])

    ca, cb = st.columns(2)
    with ca:
        if st.button("末尾に追加", key="badd_end", use_container_width=True):
            slides.append(_defaults(add_type))
            st.session_state.sel = len(slides) - 1
            _clear_form_state()
            st.rerun()
    with cb:
        if st.button("次に挿入", key="badd_here", use_container_width=True):
            idx = st.session_state.sel + 1
            slides.insert(idx, _defaults(add_type))
            st.session_state.sel = idx
            _clear_form_state()
            st.rerun()

# ── Right: Slide editor ────────────────────────────────────────

with col_editor:
    sel = st.session_state.sel
    if not slides or sel >= len(slides):
        st.info("左のリストからスライドを選択してください")
        st.stop()

    slide = slides[sel]
    stype = slide.get("type", "bullet")
    info  = SLIDE_TYPES.get(stype, {})

    st.markdown(f"### {info.get('icon','')}  スライド {sel+1}  ·  {info.get('label','')}")
    st.caption(info.get("desc", ""))

    # Type change
    new_type = st.selectbox(
        "スライドの種類を変更",
        options=list(SLIDE_TYPES.keys()),
        format_func=lambda k: f"{SLIDE_TYPES[k]['icon']}  {SLIDE_TYPES[k]['label']}",
        index=list(SLIDE_TYPES.keys()).index(stype),
        key=f"type_change_{sel}",
    )
    if new_type != stype:
        fresh = _defaults(new_type)
        for carry in ("slide_title", "title", "subtitle"):
            if carry in slide and carry in fresh:
                fresh[carry] = slide[carry]
        slides[sel] = fresh
        _clear_form_state()
        st.rerun()

    st.markdown("---")

    fields = SLIDE_FIELDS.get(stype, [])

    # ── KPI3: special 3-column layout ─────────────────────────
    if stype == "kpi3":
        # Slide title
        f0 = fields[0]
        wk = f"f_{sel}_{f0['key']}"
        if wk not in st.session_state:
            st.session_state[wk] = slide.get(f0["key"], f0["default"])
        st.text_input(f0["label"], key=wk,
                      on_change=_on_change, args=(sel, f0["key"]))

        kpi_cols = st.columns(3)
        for i in range(1, 4):
            with kpi_cols[i-1]:
                st.markdown(f"**指標 {i}**")
                for sub_key, sub_lbl in [
                    (f"kpi{i}_label", "ラベル"),
                    (f"kpi{i}_value", "数値"),
                    (f"kpi{i}_unit",  "単位"),
                    (f"kpi{i}_note",  "補足"),
                ]:
                    wk = f"f_{sel}_{sub_key}"
                    fdef = next((f for f in fields if f["key"] == sub_key), None)
                    if not fdef:
                        continue
                    if wk not in st.session_state:
                        st.session_state[wk] = slide.get(sub_key, fdef["default"])
                    st.text_input(sub_lbl, key=wk,
                                  on_change=_on_change, args=(sel, sub_key))

    # ── All other slide types ──────────────────────────────────
    else:
        for fdef in fields:
            wk = f"f_{sel}_{fdef['key']}"
            if wk not in st.session_state:
                st.session_state[wk] = slide.get(fdef["key"], fdef["default"])

            if fdef["type"] == "textarea":
                hint = ""
                if "csv" in fdef["key"]:
                    hint = "カンマ区切り、1行1データ"
                elif "bullets" in fdef["key"]:
                    hint = "1行に1つの項目を入力"
                st.text_area(
                    fdef["label"] + (f"  _{hint}_" if hint else ""),
                    key=wk, height=130,
                    on_change=_on_change, args=(sel, fdef["key"]),
                )
            else:
                st.text_input(
                    fdef["label"], key=wk,
                    on_change=_on_change, args=(sel, fdef["key"]),
                )

    st.markdown("---")

    # Quick preview hint
    tip_map = {
        "chart_bar":  "データ例: `2021,100`  `2022,120`  （ラベル,数値）",
        "chart_line": "データ例: `2021,100`  `2022,120`  （ラベル,数値）",
        "chart_pie":  "データ例: `カテゴリA,35`  `カテゴリB,28`  （ラベル,数値）",
        "table":      "1行目がヘッダー行になります。カンマで列を区切ってください。",
        "kpi3":       "数値欄には `¥120M` や `+23%` のような文字列も入力できます。",
        "quote":      "短くインパクトのある一文が効果的です。",
    }
    if stype in tip_map:
        st.info(f"💡 {tip_map[stype]}")
