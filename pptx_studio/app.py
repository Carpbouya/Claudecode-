"""
パワポスタジオ — デザインシステム搭載のPowerPointビルダー
非エンジニアがプロ品質のスライドをノーコードで作れる Streamlit アプリ

起動: streamlit run app.py
"""
import io
import json
import streamlit as st
from builder import build_pptx, SLIDE_TYPES, SLIDE_FIELDS
from ds import THEMES, with_brand
from importer import extract_brand

st.set_page_config(
    page_title="パワポスタジオ",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ─────────────────────────────────────────────────
st.markdown("""
<style>
[data-testid="stSidebar"] > div:first-child { background: #1F2937; }
[data-testid="stSidebar"] h1,[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,[data-testid="stSidebar"] p,
[data-testid="stSidebar"] label,[data-testid="stSidebar"] span,
[data-testid="stSidebar"] .stRadio label { color: #F9FAFB !important; }
[data-testid="stSidebar"] .stCaption { color: #9CA3AF !important; }
[data-testid="stSidebar"] .stTextInput input,
[data-testid="stSidebar"] .stTextArea textarea {
    background: #374151 !important;
    color: #F9FAFB !important;
    border-color: #4B5563 !important;
}
[data-testid="stSidebar"] .stExpander { border-color: #374151 !important; }
#MainMenu, footer { visibility: hidden; }
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
         "kpi1_label": "売上高", "kpi1_value": "¥120M", "kpi1_unit": "前年比 +20%", "kpi1_note": "",
         "kpi2_label": "顧客数", "kpi2_value": "1,580", "kpi2_unit": "前年比 +350件",  "kpi2_note": "",
         "kpi3_label": "NPS",   "kpi3_value": "72",    "kpi3_unit": "業界平均 +18pt", "kpi3_note": ""},
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

if "sel"           not in st.session_state: st.session_state.sel           = 0
if "theme_key"     not in st.session_state: st.session_state.theme_key     = "navy"
if "company"       not in st.session_state: st.session_state.company       = ""
if "logo_bytes"    not in st.session_state: st.session_state.logo_bytes    = None
if "logo_header"   not in st.session_state: st.session_state.logo_header   = True
if "use_custom_c"  not in st.session_state: st.session_state.use_custom_c  = False
if "custom_pri"    not in st.session_state: st.session_state.custom_pri    = "#1F2937"
if "custom_acc"    not in st.session_state: st.session_state.custom_acc    = "#3B82F6"
if "import_result" not in st.session_state: st.session_state.import_result = None
if "import_fname"  not in st.session_state: st.session_state.import_fname  = ""

slides = st.session_state.slides

# ── Sidebar ────────────────────────────────────────────────────

with st.sidebar:

    # ── 1. デザインシステム ────────────────────────────────────
    st.markdown("## 🎨 デザインシステム")
    st.markdown("#### ベーステーマ")
    selected_theme = st.radio(
        "theme",
        options=list(THEMES.keys()),
        format_func=lambda k: f"{THEMES[k].emoji}  {THEMES[k].name}",
        index=list(THEMES.keys()).index(st.session_state.theme_key),
        label_visibility="collapsed",
    )
    st.session_state.theme_key = selected_theme
    theme = THEMES[selected_theme]

    # ── 1.5 既存PPTXからデザインを読み込む ────────────────────
    with st.expander("📂 既存スライドからデザインを読み込む"):
        st.caption("社内の既存PPTXをアップロードしてカラー・ロゴを自動抽出します")
        pptx_up = st.file_uploader(
            "pptx_import",
            type=["pptx"],
            key="pptx_import",
            label_visibility="collapsed",
        )
        if pptx_up is not None and pptx_up.name != st.session_state.import_fname:
            with st.spinner("デザインを解析中…"):
                try:
                    r = extract_brand(pptx_up.read())
                    st.session_state.import_result = r
                    st.session_state.import_fname  = pptx_up.name
                except Exception as e:
                    st.error(f"解析エラー: {e}")

        ir = st.session_state.import_result
        if ir:
            palette = ir.get("palette", [])

            # Palette swatches — hover to see hex value
            if palette:
                sw = '<div style="display:flex;flex-wrap:wrap;gap:5px;margin:6px 0 8px">'
                for col in palette[:12]:
                    sw += (
                        f'<div title="{col}" style="width:24px;height:24px;'
                        f'background:{col};border-radius:4px;cursor:default;'
                        f'border:1.5px solid rgba(255,255,255,0.20)"></div>'
                    )
                sw += '</div>'
                st.markdown(sw, unsafe_allow_html=True)

            # Color selectors — pick from palette with swatch preview label
            def _fmt(h):
                return f"{h}"

            opts = palette if palette else [ir["primary"], ir["accent"]]

            pri_idx = opts.index(ir["primary"]) if ir["primary"] in opts else 0
            acc_idx = opts.index(ir["accent"])  if ir["accent"]  in opts else min(1, len(opts)-1)

            pc, ac = st.columns(2)
            with pc:
                sel_pri = st.selectbox(
                    "Primary", options=opts, index=pri_idx,
                    key="import_sel_pri",
                    format_func=_fmt,
                )
                st.markdown(
                    f'<div style="width:100%;height:18px;background:{sel_pri};'
                    f'border-radius:3px;margin-top:-8px"></div>',
                    unsafe_allow_html=True,
                )
            with ac:
                sel_acc = st.selectbox(
                    "Accent", options=opts, index=acc_idx,
                    key="import_sel_acc",
                    format_func=_fmt,
                )
                st.markdown(
                    f'<div style="width:100%;height:18px;background:{sel_acc};'
                    f'border-radius:3px;margin-top:-8px"></div>',
                    unsafe_allow_html=True,
                )

            if ir.get("logo_bytes"):
                st.image(io.BytesIO(ir["logo_bytes"]), width=110, caption="検出されたロゴ")

            if st.button("このデザインを適用", use_container_width=True,
                         type="primary", key="apply_import"):
                st.session_state.use_custom_c = True
                st.session_state.custom_pri   = sel_pri
                st.session_state.custom_acc   = sel_acc
                if ir.get("logo_bytes"):
                    st.session_state.logo_bytes = ir["logo_bytes"]
                st.success("適用しました！")
                st.rerun()

    st.markdown("---")

    # ── 2. ブランドカラーカスタマイズ ─────────────────────────
    with st.expander("🎨 ブランドカラーをカスタマイズ"):
        st.session_state.use_custom_c = st.checkbox(
            "カスタムカラーを使用", value=st.session_state.use_custom_c
        )
        if st.session_state.use_custom_c:
            c1, c2 = st.columns(2)
            with c1:
                st.session_state.custom_pri = st.color_picker(
                    "プライマリ", value=st.session_state.custom_pri
                )
            with c2:
                st.session_state.custom_acc = st.color_picker(
                    "アクセント", value=st.session_state.custom_acc
                )
            theme = with_brand(
                theme,
                primary=st.session_state.custom_pri,
                accent=st.session_state.custom_acc,
            )

    # Color token preview
    swatches = [
        ("Primary", theme.colors.primary),
        ("Accent",  theme.colors.accent),
        ("Soft",    theme.colors.accent_soft),
        ("Surface", theme.colors.surface_alt),
    ]
    sw = '<div style="display:flex;gap:8px;margin:6px 0 4px">'
    for name, col in swatches:
        sw += (
            f'<div style="text-align:center">'
            f'<div style="width:34px;height:34px;background:{col};border-radius:6px;'
            f'border:2px solid rgba(255,255,255,0.15)"></div>'
            f'<div style="font-size:8px;color:#9CA3AF;margin-top:3px">{name}</div>'
            f'</div>'
        )
    sw += '</div>'
    st.markdown(sw, unsafe_allow_html=True)

    with st.expander("タイポグラフィ詳細"):
        st.markdown(f"""
| トークン | サイズ |
|---------|-------|
| タイトル（大） | {theme.typo.sz_huge}pt |
| スライドタイトル | {theme.typo.sz_h1}pt |
| KPI数値 | {theme.typo.sz_kpi}pt |
| 本文 | {theme.typo.sz_body}pt |
| キャプション | {theme.typo.sz_sm}pt |
        """)

    st.markdown("---")

    # ── 3. ブランドロゴ ────────────────────────────────────────
    st.markdown("#### 🏢 ブランドロゴ")

    logo_file = st.file_uploader(
        "logo_upload",
        type=["png", "jpg", "jpeg"],
        label_visibility="collapsed",
        help="PNG または JPG をアップロード",
    )
    if logo_file is not None:
        st.session_state.logo_bytes = logo_file.read()

    if st.session_state.logo_bytes:
        st.image(
            io.BytesIO(st.session_state.logo_bytes),
            width=160,
            caption="アップロード済みロゴ",
        )
        st.session_state.logo_header = st.checkbox(
            "全スライドのヘッダーに表示",
            value=st.session_state.logo_header,
        )
        st.caption("タイトルスライドには常に表示されます")
        if st.button("ロゴを削除", key="del_logo"):
            st.session_state.logo_bytes = None
            st.rerun()
    else:
        st.caption("PNG / JPG をアップロードするとタイトルスライドと各スライドのヘッダーに自動配置されます")

    st.markdown("---")

    # ── 4. 会社・組織名 ────────────────────────────────────────
    st.markdown("#### 会社・組織名")
    st.session_state.company = st.text_input(
        "company_name",
        value=st.session_state.company,
        placeholder="フッターに表示（任意）",
        label_visibility="collapsed",
    )

    st.markdown("---")

    # ── 5. ブランドプリセット ──────────────────────────────────
    with st.expander("💾 ブランドプリセット"):
        st.caption("デザイン設定をJSONで保存・共有できます")
        if st.button("プリセットをダウンロード", use_container_width=True):
            preset = {
                "theme_key":   st.session_state.theme_key,
                "company":     st.session_state.company,
                "use_custom":  st.session_state.use_custom_c,
                "custom_pri":  st.session_state.custom_pri,
                "custom_acc":  st.session_state.custom_acc,
                "logo_header": st.session_state.logo_header,
            }
            st.download_button(
                "📥 brand_preset.json",
                data=json.dumps(preset, ensure_ascii=False, indent=2),
                file_name="brand_preset.json",
                mime="application/json",
                use_container_width=True,
            )
        preset_file = st.file_uploader(
            "プリセットを読み込む", type=["json"],
            key="preset_upload", label_visibility="collapsed"
        )
        if preset_file:
            try:
                p = json.load(preset_file)
                st.session_state.theme_key    = p.get("theme_key",   "navy")
                st.session_state.company      = p.get("company",     "")
                st.session_state.use_custom_c = p.get("use_custom",  False)
                st.session_state.custom_pri   = p.get("custom_pri",  "#1F2937")
                st.session_state.custom_acc   = p.get("custom_acc",  "#3B82F6")
                st.session_state.logo_header  = p.get("logo_header", True)
                st.success("読み込みました")
                st.rerun()
            except Exception as e:
                st.error(f"読み込みエラー: {e}")

    st.markdown("---")

    # ── 6. エクスポート ────────────────────────────────────────
    st.markdown(f"#### エクスポート  `{len(slides)} スライド`")

    if st.button("⬇️  PowerPoint を生成", use_container_width=True, type="primary"):
        with st.spinner("スライド生成中…"):
            buf = build_pptx(
                slides,
                theme,
                company=st.session_state.company,
                logo_bytes=st.session_state.logo_bytes,
                logo_in_header=st.session_state.logo_header,
            )
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
            if st.button(
                f"{info.get('icon','📄')}  {i+1}. {preview}",
                key=f"bsel_{i}",
                use_container_width=True,
                type="primary" if is_sel else "secondary",
            ):
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

    # ── KPI3: 3-column layout ─────────────────────────────────
    if stype == "kpi3":
        f0 = fields[0]
        wk = f"f_{sel}_{f0['key']}"
        if wk not in st.session_state:
            st.session_state[wk] = slide.get(f0["key"], f0["default"])
        st.text_input(f0["label"], key=wk, on_change=_on_change, args=(sel, f0["key"]))

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
                    st.text_input(sub_lbl, key=wk, on_change=_on_change, args=(sel, sub_key))

    # ── All other slide types ─────────────────────────────────
    else:
        for fdef in fields:
            wk = f"f_{sel}_{fdef['key']}"
            if wk not in st.session_state:
                st.session_state[wk] = slide.get(fdef["key"], fdef["default"])

            if fdef["type"] == "textarea":
                hint = ""
                if "csv" in fdef["key"]:
                    hint = "カンマ区切り、1行1データ"
                elif "bullets" in fdef["key"] or "content" in fdef["key"]:
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

    tip_map = {
        "chart_bar":  "データ例: `2021,100`  `2022,120`  （ラベル,数値）",
        "chart_line": "データ例: `2021,100`  `2022,120`  （ラベル,数値）",
        "chart_pie":  "データ例: `カテゴリA,35`  `カテゴリB,28`  （ラベル,数値）",
        "table":      "1行目がヘッダー行になります。カンマで列を区切ってください。",
        "kpi3":       "数値欄には `¥120M` や `+23%` のような文字列も入力できます。",
        "quote":      "短くインパクトのある一文が効果的です。",
        "title":      "サイドバーからロゴをアップロードするとタイトルスライドに自動配置されます。",
    }
    if stype in tip_map:
        st.info(f"💡 {tip_map[stype]}")
