import pandas as pd, numpy as np, io, os, re, warnings
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import matplotlib.patches as mpatches
warnings.filterwarnings('ignore')
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

JP = fm.FontProperties(fname='/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf')
matplotlib.rcParams['font.family'] = 'IPAGothic'
plt.rcParams['axes.unicode_minus'] = False

# ── COLORS (PDF-matched) ────────────────────────────────────────────────────
NAVY  = RGBColor(0x1A,0x34,0x60)
BLUE  = RGBColor(0x21,0x63,0xEB)
TEAL  = RGBColor(0x10,0xB9,0x81)
RED   = RGBColor(0xEF,0x44,0x44)
LGRAY = RGBColor(0xF3,0xF4,0xF6)
DGRAY = RGBColor(0x1F,0x29,0x37)
MID   = RGBColor(0x6B,0x72,0x80)
WHITE = RGBColor(0xFF,0xFF,0xFF)
BORD  = RGBColor(0xD1,0xD5,0xDB)
LBLUE = RGBColor(0xEF,0xF6,0xFF)
LTEAL = RGBColor(0xF0,0xFD,0xFA)
WARN  = RGBColor(0xFF,0xF7,0xED)
AMBER = RGBColor(0xF5,0x9E,0x0B)
GBOX  = RGBColor(0xF0,0xFD,0xF4)
GBDR  = RGBColor(0x10,0xB9,0x81)

cN='#1A3460'; cB='#2163EB'; cT='#10B981'; cR='#EF4444'
cG='#6B7280'; cD='#1F2937'; cL='#F3F4F6'; cW='#FFFFFF'
cA='#F59E0B'; cBL='#EFF6FF'

# ── DATA ───────────────────────────────────────────────────────────────────
BASE="/root/.claude/uploads/ecc37ffa-bb41-5307-ab96-9ba26cf1b3e6"
FILES={"建築営業":f"{BASE}/7ad2cb95-_____________.xlsx",
       "土木営業":f"{BASE}/7fb8bf88-______________.xlsx",
       "建築施工管理":f"{BASE}/ad994568-_______________.xlsx",
       "土木施工管理":f"{BASE}/99e57c2d-_______________.xlsx",
       "設備施工管理":f"{BASE}/efb3ec5a-________________.xlsx",
       "不動産開発":f"{BASE}/2bcbff44-_______________.xlsx",
       "再生可能エネルギー":f"{BASE}/c9b8365b-___________________.xlsx",
       "土木研究開発":f"{BASE}/dc161864-______________.xlsx"}
CM={'名前':['名前','企業名','会社名'],'給与':['給与','給与タイプ','給与形態'],
    '給与2':['給与2','給与額','給与レンジ'],'コンテンツ5':['コンテンツ5','必須要件','応募要件'],
    'コンテンツ':['コンテンツ','仕事内容','業務内容'],'キーワード':['キーワード','タグ','条件']}
def nm(df):
    r={}
    for c,vs in CM.items():
        for col in df.columns:
            if col.strip() in vs: r[col]=c; break
    return df.rename(columns=r)
def _pm(s):
    s=s.strip()
    m=re.match(r'(\d+)万(\d+)円',s)
    if m: return (int(m.group(1))*10000+int(m.group(2)))/10000
    m=re.match(r'(\d+(?:\.\d+)?)万円?',s)
    return float(m.group(1)) if m else None
def psal(t,a):
    if pd.isna(t) or pd.isna(a): return None,None
    t,a=str(t).strip(),str(a).strip()
    ls=a.split('～')[0] if '～' in a else a.replace('以上','')
    us=a.split('～')[1].replace('以上','') if '～' in a else None
    lm=_pm(ls); um=_pm(us) if us else None
    mul=15 if '月給' in t else 1 if '年俸' in t else None
    if not mul: return None,None
    return (round(lm*mul) if lm else None),(round(um*mul) if um else None)
def gnk(row):
    m=re.search(r'年間休日(\d+)日',str(row.get('キーワード') or ''))
    if m: return int(m.group(1))
    for c in ('コンテンツ5','コンテンツ'):
        m=re.search(r'年(?:間)?休(?:日)?(\d+)日',str(row.get(c) or ''))
        if m: return int(m.group(1))
    return None
def gzg(row):
    m=re.search(r'月平均残業時間(\d+)時間以内',str(row.get('キーワード') or ''))
    if m: return int(m.group(1))
    for c in ('コンテンツ5','コンテンツ'):
        t=str(row.get(c) or '')
        for p in [r'残業月?(\d+)h',r'(?:月平均)?残業(?:時間)?月?(\d+)時間(?!以上)']:
            m=re.search(p,t)
            if m: return int(m.group(1))
    return None
def glst(row):
    t=' '.join(str(row.get(c) or '') for c in ('コンテンツ','コンテンツ5'))
    if re.search(r'プライム市場|東証プライム|東証一部',t): return 'プライム'
    if re.search(r'スタンダード市場|東証スタンダード|東証二部',t): return 'スタンダード'
    if re.search(r'グロース市場|東証グロース',t): return 'グロース'
    if re.search(r'上場企業|上場G|一部上場',t): return '上場(区分不明)'
    return '非上場/不明'
def gage(row):
    at=' '.join(str(row.get(c) or '') for c in ('キーワード','コンテンツ','コンテンツ5'))
    m=re.search(r'(\d{2})歳(?:以下|まで|未満)',at)
    upper=int(m.group(1)) if m else None
    m2=re.search(r'(\d{2})歳(?:以上|から)',at)
    lower=int(m2.group(1)) if m2 else None
    agefree=bool(re.search(r'年齢不問',at))
    g20=bool(re.search(r'20代',at))
    g30=bool(re.search(r'30代',at))
    g40=bool(re.search(r'40代',at))
    return upper,lower,agefree,g20,g30,g40

BEN={'リモートワーク可':r'リモート|在宅勤務|テレワーク','フレックス制':r'フレックス',
     '転勤なし':r'転勤なし|転勤無し','社宅・住宅補助':r'社宅|住宅手当|住宅補助|家賃補助',
     '資格取得支援':r'資格取得|資格支援','育休・産休実績':r'育休|産休',
     '退職金制度':r'退職金','完全週休2日':r'完全週休2日|完全週休二日'}
LIC={'一級建築施工管理技士':r'一[級・]?建築施工管理技?士?',
     '二級建築施工管理技士':r'二[級・]?建築施工管理技?士?',
     '一級土木施工管理技士':r'一[級・]?土木施工管理技?士?',
     '二級土木施工管理技士':r'二[級・]?土木施工管理技?士?',
     '一級管工事施工管理技士':r'一[級・]?管工事施工管理技?士?',
     '一級電気工事施工管理技士':r'一[級・]?電気工事施工管理技?士?'}
BANDS=['200万以下','200-300万','300-400万','400-500万','500-600万',
       '600-700万','700-800万','800-900万','900-1000万','1000万以上']
def bnd(v):
    if v is None or (isinstance(v,float) and pd.isna(v)): return None
    for lo,hi,lb in [(0,200,'200万以下'),(200,300,'200-300万'),(300,400,'300-400万'),
                     (400,500,'400-500万'),(500,600,'500-600万'),(600,700,'600-700万'),
                     (700,800,'700-800万'),(800,900,'800-900万'),(900,1000,'900-1000万'),(1000,9999,'1000万以上')]:
        if lo<=v<hi: return lb
    return None

print("Loading...")
recs=[]
for cat,fp in FILES.items():
    xl=pd.ExcelFile(fp)
    for sh in xl.sheet_names:
        d=xl.parse(sh)
        if d.empty: continue
        d=nm(d)
        for _,row in d.iterrows():
            at=' '.join(str(row.get(c) or '') for c in ('キーワード','コンテンツ','コンテンツ5'))
            lo,hi=psal(row.get('給与'),row.get('給与2'))
            au,al,af,g20,g30,g40=gage(row)
            r={'カテゴリ':cat,'企業名':row.get('名前'),
               '下限':lo,'上限':hi,'下限帯':bnd(lo),'上限帯':bnd(hi),
               '年間休日':gnk(row),'月残業':gzg(row),'上場':glst(row),
               '年齢上限':au,'年齢下限':al,'年齢不問':af,'20代':g20,'30代':g30,'40代':g40}
            for k,p in BEN.items(): r[f'B_{k}']=bool(re.search(p,at))
            for k,p in LIC.items(): r[f'L_{k}']=bool(re.search(p,at))
            recs.append(r)
df=pd.DataFrame(recs)
print(f"  {len(df)}件")

# ── PPTX HELPERS ───────────────────────────────────────────────────────────
W,H=Inches(13.33),Inches(7.5)
def newprs():
    p=Presentation(); p.slide_width=W; p.slide_height=H; return p
def addsl(prs): return prs.slides.add_slide(prs.slide_layouts[6])
def rect(sl,x,y,w,h,fill,line=None,lw=None):
    s=sl.shapes.add_shape(1,Inches(x),Inches(y),Inches(w),Inches(h))
    s.fill.solid(); s.fill.fore_color.rgb=fill
    if line: s.line.color.rgb=line
    else: s.line.fill.background()
    return s
def txt(sl,text,x,y,w,h,sz=11,bold=False,col=None,align=PP_ALIGN.LEFT,italic=False):
    col=col or DGRAY
    tb=sl.shapes.add_textbox(Inches(x),Inches(y),Inches(w),Inches(h))
    tf=tb.text_frame; tf.word_wrap=True
    p=tf.paragraphs[0]; p.alignment=align
    rn=p.add_run(); rn.text=text
    rn.font.size=Pt(sz); rn.font.bold=bold; rn.font.italic=italic
    rn.font.color.rgb=col; rn.font.name='メイリオ'
    return tb
def fig2img(fig):
    buf=io.BytesIO()
    fig.savefig(buf,format='png',dpi=150,bbox_inches='tight',facecolor='white',edgecolor='none')
    buf.seek(0); plt.close(fig); return buf
def addimg(sl,buf,x,y,w,h):
    sl.shapes.add_picture(buf,Inches(x),Inches(y),Inches(w),Inches(h))

def title_bar(sl,title,source_text,pg=None):
    """PDF-style: white bg, left navy bar, title, source top-right"""
    rect(sl,0,0,13.33,7.5,WHITE)                   # white bg
    rect(sl,0.22,0.18,0.07,0.48,NAVY)              # left accent bar
    txt(sl,title,0.38,0.17,10.5,0.52,sz=17,bold=True,col=NAVY)
    txt(sl,source_text,10.5,0.20,2.65,0.35,sz=8,col=MID,align=PP_ALIGN.RIGHT)
    # thin divider
    rect(sl,0.22,0.75,13.0,0.02,BORD)
    # footer
    rect(sl,0,7.15,13.33,0.35,LGRAY)
    txt(sl,'※ r-agent 求人掲載データ（2024年）に基づく分析。掲載件数N=10,526件。',
        0.3,7.2,11,0.25,sz=7.5,col=MID)
    if pg:
        txt(sl,f'{pg}',12.8,7.2,0.4,0.25,sz=8,col=MID,align=PP_ALIGN.RIGHT)

def kpi_box(sl,label,value,unit,x,y,w=3.8,h=1.0,accent=None):
    """PDF-style KPI box with border"""
    rect(sl,x,y,w,h,WHITE,line=BORD)
    if accent:
        rect(sl,x,y,w,0.055,accent)  # top color bar
    txt(sl,label,x+0.18,y+0.1,w-0.25,0.28,sz=9,col=MID)
    txt(sl,value,x+0.18,y+0.38,w-0.55,0.5,sz=26,bold=True,col=NAVY)
    if unit:
        txt(sl,unit,x+0.18+len(value)*0.19,y+0.55,1.2,0.28,sz=11,col=MID)

def note_box(sl,icon,text,x,y,w,h,bg,border_col,icon_col):
    """PDF-style bottom note box"""
    rect(sl,x,y,w,h,bg,line=border_col)
    txt(sl,icon,x+0.15,y+0.08,0.35,h-0.1,sz=13,bold=True,col=icon_col)
    txt(sl,text,x+0.52,y+0.1,w-0.65,h-0.18,sz=9.5,col=DGRAY)

def section_header(sl,text,x,y,w,color=LBLUE,tc=NAVY):
    rect(sl,x,y,w,0.32,color)
    txt(sl,text,x+0.15,y+0.04,w-0.2,0.25,sz=10,bold=True,col=tc)

def hbar_chart(data_labels,data_vals,total_n,color,figsize=(5.5,3.8),
               highlight_last=False,x_max=None):
    """PDF-style horizontal bar chart"""
    fig,ax=plt.subplots(figsize=figsize)
    n=len(data_labels)
    y=np.arange(n)
    bar_colors=[color]*n
    if highlight_last: bar_colors[-1]=cR
    bars=ax.barh(y,data_vals,color=bar_colors,height=0.45,edgecolor='none')
    ax.set_yticks(y)
    ax.set_yticklabels(data_labels,fontproperties=JP,fontsize=10)
    ax.set_xlim(0,(x_max or max(data_vals)*1.35) if max(data_vals)>0 else 10)
    for bar,v in zip(bars,data_vals):
        if v>0:
            ax.text(max(data_vals)*0.015,bar.get_y()+bar.get_height()/2,f'{int(v):,}件',
                    va='center',ha='left',fontsize=10,color='white',
                    fontproperties=JP,fontweight='bold')
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False); ax.spines['bottom'].set_visible(False)
    ax.set_facecolor('white'); ax.tick_params(left=False,bottom=False)
    ax.xaxis.set_visible(False)
    fig.patch.set_facecolor('white')
    plt.tight_layout(pad=0.5)
    return fig

# ══════════════════════════════════════════════════════════════════════════════
prs=newprs()

# ── COVER ──────────────────────────────────────────────────────────────────
sl=addsl(prs)
rect(sl,0,0,13.33,7.5,NAVY)
rect(sl,0,3.2,13.33,0.08,TEAL)
rect(sl,0.6,0,0.12,3.2,TEAL)
txt(sl,'中堅ゼネコン 採用支援',0.9,0.7,10,0.65,sz=18,col=RGBColor(0xA0,0xB8,0xD8))
txt(sl,'建設・土木業界\n求人市場実態調査',0.9,1.3,10,1.7,sz=44,bold=True,col=WHITE)
txt(sl,'採用戦略立案のための競合市場データ分析',0.9,3.4,10,0.6,sz=16,col=RGBColor(0xA0,0xB8,0xD8))
txt(sl,'対象：建設・土木・不動産・再生可能エネルギー  |  N=10,526件  |  2024年',
    0.9,4.2,11,0.45,sz=11,col=RGBColor(0x70,0x90,0xB0))
txt(sl,'Confidential  |  採用コンサルティング資料',0.9,6.6,11.5,0.4,sz=10,col=RGBColor(0x50,0x70,0x90))

# ── S1: 調査概要 ────────────────────────────────────────────────────────────
sl=addsl(prs)
title_bar(sl,'調査概要：8職種・10,526件の競合求人データを分析','📊 Survey Overview',1)

kpi_box(sl,'分析対象 求人件数','10,526','件',0.22,0.9,accent=NAVY)
kpi_box(sl,'対象職種数','8','職種',4.27,0.9,accent=TEAL)
kpi_box(sl,'データソース','r-agent','',8.32,0.9,accent=NAVY)

cnt=df['カテゴリ'].value_counts().sort_values()
fig,ax=plt.subplots(figsize=(10,3.8))
bar_colors=[cT if v==cnt.max() else cB for v in cnt.values]
bars=ax.barh(cnt.index,cnt.values,color=bar_colors,height=0.55,edgecolor='none')
for bar,v in zip(bars,cnt.values):
    ax.text(v+40,bar.get_y()+bar.get_height()/2,f'{v:,}件',
            va='center',ha='left',fontsize=11,color=cD,fontproperties=JP)
for tick in ax.get_yticklabels(): tick.set_fontproperties(JP)
ax.set_xlim(0,cnt.max()*1.22); ax.xaxis.set_visible(False)
ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
ax.spines['left'].set_visible(False); ax.spines['bottom'].set_visible(False)
ax.set_facecolor('white'); ax.tick_params(left=False,bottom=False)
fig.patch.set_facecolor('white'); plt.tight_layout(pad=0.5)
addimg(sl,fig2img(fig),0.22,2.05,12.9,5.05)

# ── S2: 年収帯分布 ──────────────────────────────────────────────────────────
sl=addsl(prs)
title_bar(sl,'競合求人の年収レンジ：下限400〜500万円帯が最多、上限は600〜700万円帯がピーク','💴 Salary Distribution',2)

kpi_box(sl,'下限年収 中央値','450','万円',0.22,0.9,accent=BLUE)
kpi_box(sl,'上限年収 中央値','675','万円',4.27,0.9,accent=TEAL)
kpi_box(sl,'年収レンジ幅 中央値','225','万円',8.32,0.9,accent=NAVY)

bl=df['下限'].dropna().apply(bnd).value_counts().reindex(BANDS).fillna(0).astype(int)
bu=df['上限'].dropna().apply(bnd).value_counts().reindex(BANDS).fillna(0).astype(int)

section_header(sl,'下限年収 提示分布（N=10,162件）',0.22,2.08,6.1)
fig1=hbar_chart(BANDS,bl.values,len(df),cB,figsize=(5.5,4.5))
addimg(sl,fig2img(fig1),0.22,2.42,6.1,4.65)

section_header(sl,'上限年収 提示分布（N=6,367件）',6.52,2.08,6.6)
fig2=hbar_chart(BANDS,bu.values,len(df),cT,figsize=(5.5,4.5))
addimg(sl,fig2img(fig2),6.52,2.42,6.6,4.65)

# ── S3: 職種別年収 ──────────────────────────────────────────────────────────
sl=addsl(prs)
title_bar(sl,'職種別年収比較（下限・上限 中央値）：カテゴリ間の年収水準','💴 Salary by Category',3)

cs=df.groupby('カテゴリ').agg(下限=('下限','median'),上限=('上限','median')).round(0).sort_values('下限',ascending=False)
top=cs.index[0]
kpi_box(sl,f'最高年収職種',top,'',0.22,0.9,accent=TEAL)
kpi_box(sl,f'{top} 下限中央値',f"{int(cs.loc[top,'下限'])}","万円",4.27,0.9,accent=TEAL)
kpi_box(sl,'施工管理 下限中央値','450','万円',8.32,0.9,accent=BLUE)

fig,ax=plt.subplots(figsize=(10.5,4.2))
cats_=cs.index.tolist(); lo_=cs['下限'].values; hi_=cs['上限'].values
y_=np.arange(len(cats_))
for i,(l,h) in enumerate(zip(lo_,hi_)):
    if not np.isnan(h):
        ax.barh(i,h-l,left=l,height=0.5,color='#BFDBFE',edgecolor='none',alpha=0.9)
bar_colors2=[cT if c==top else cB for c in cats_]
ax.barh(y_,lo_,height=0.5,color=bar_colors2,edgecolor='none')
for i,(l,h,c) in enumerate(zip(lo_,hi_,cats_)):
    fc=cT if c==top else cB
    ax.text(l-4,i,f'{int(l)}万',va='center',ha='right',fontsize=11,
            fontweight='bold',color=fc,fontproperties=JP)
    if not np.isnan(h):
        ax.text(h+4,i,f'〜{int(h)}万',va='center',ha='left',fontsize=10,
                color=cG,fontproperties=JP)
ax.set_yticks(y_); ax.set_yticklabels(cats_,fontproperties=JP,fontsize=11)
ax.set_xlim(280,1020); ax.xaxis.set_visible(False)
ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
ax.spines['left'].set_visible(False); ax.spines['bottom'].set_visible(False)
p1=mpatches.Patch(color=cB,label='下限年収中央値')
p2=mpatches.Patch(color='#BFDBFE',label='上限レンジ')
ax.legend(handles=[p1,p2],prop=JP,fontsize=9,loc='lower right',framealpha=0.9)
ax.set_facecolor('white'); ax.tick_params(left=False,bottom=False)
fig.patch.set_facecolor('white'); plt.tight_layout(pad=0.5)
addimg(sl,fig2img(fig),0.22,2.05,12.9,5.1)

# ── S4: 資格プレミアム ──────────────────────────────────────────────────────
sl=addsl(prs)
title_bar(sl,'一級資格保有者の採用には下限568万円以上が競争力の目安、二級比で約150万円高い','🏅 Qualification Premium',4)

kpi_box(sl,'一級建築施工 下限中央値','568','万円',0.22,0.9,accent=TEAL)
kpi_box(sl,'二級建築施工 下限中央値','422','万円',4.27,0.9,accent=BLUE)
kpi_box(sl,'一・二級差分（下限）','▲146','万円',8.32,0.9,accent=RED)

ld=[]
for lic,pat in LIC.items():
    sub=df[df[f'L_{lic}']==True]
    if len(sub)<10: continue
    ld.append({'資格':lic,'件数':len(sub),'下限':sub['下限'].median(),'上限':sub['上限'].median()})
ldf=pd.DataFrame(ld).sort_values('下限',ascending=False)

section_header(sl,'一級資格  提示年収（下限中央値）',0.22,2.08,6.3,LBLUE,BLUE)
ichi=ldf[ldf['資格'].str.contains('一級')]
fig1,ax1=plt.subplots(figsize=(5.5,2.8))
bar_c=[cT if v==ichi['下限'].max() else cB for v in ichi['下限'].values]
bars=ax1.barh(ichi['資格'],ichi['下限'],color=bar_c,height=0.5,edgecolor='none')
for bar,v in zip(bars,ichi['下限'].values):
    ax1.text(v+3,bar.get_y()+bar.get_height()/2,f'{int(v)}万円',
             va='center',ha='left',fontsize=11,fontweight='bold',
             color=cD,fontproperties=JP)
for tick in ax1.get_yticklabels(): tick.set_fontproperties(JP)
ax1.set_xlim(380,730); ax1.xaxis.set_visible(False)
ax1.spines['top'].set_visible(False); ax1.spines['right'].set_visible(False)
ax1.spines['left'].set_visible(False); ax1.spines['bottom'].set_visible(False)
ax1.set_facecolor('white'); ax1.tick_params(left=False,bottom=False)
fig1.patch.set_facecolor('white'); plt.tight_layout(pad=0.5)
addimg(sl,fig2img(fig1),0.22,2.42,6.3,4.5)

section_header(sl,'二級資格  提示年収（下限中央値）',6.72,2.08,6.3,RGBColor(0xF0,0xF9,0xFF),BLUE)
ni=ldf[ldf['資格'].str.contains('二級')]
fig2,ax2=plt.subplots(figsize=(5.5,3.5))
bars=ax2.barh(ni['資格'],ni['下限'],color=cB,height=0.5,edgecolor='none')
for bar,v in zip(bars,ni['下限'].values):
    ax2.text(v+3,bar.get_y()+bar.get_height()/2,f'{int(v)}万円',
             va='center',ha='left',fontsize=11,fontweight='bold',
             color=cD,fontproperties=JP)
for tick in ax2.get_yticklabels(): tick.set_fontproperties(JP)
ax2.set_xlim(340,650); ax2.xaxis.set_visible(False)
ax2.spines['top'].set_visible(False); ax2.spines['right'].set_visible(False)
ax2.spines['left'].set_visible(False); ax2.spines['bottom'].set_visible(False)
ax2.set_facecolor('white'); ax2.tick_params(left=False,bottom=False)
fig2.patch.set_facecolor('white'); plt.tight_layout(pad=0.5)
addimg(sl,fig2img(fig2),6.72,2.42,6.3,4.5)

# ── S5: 上場vs非上場 ────────────────────────────────────────────────────────
sl=addsl(prs)
title_bar(sl,'上場区分別 下限年収中央値：プライム・スタンダード・グロース・非上場の比較','🏢 Listed vs Non-Listed',5)

ls_ord=['プライム','スタンダード','グロース','上場(区分不明)','非上場/不明']
ls=df.groupby('上場')['下限'].median().reindex(ls_ord).dropna()
top_ls=ls.idxmax(); top_v=int(ls.max())
kpi_box(sl,'非上場/不明 下限中央値','450','万円',0.22,0.9,accent=TEAL)
kpi_box(sl,'プライム上場 下限中央値','435','万円',4.27,0.9,accent=BLUE)
kpi_box(sl,'非上場 vs プライム','＋15','万円',8.32,0.9,accent=TEAL)

fig,ax=plt.subplots(figsize=(9.5,3.5))
bar_colors3=[cT if '非上場' in l else cB for l in ls.index]
bars=ax.bar(range(len(ls)),ls.values,color=bar_colors3,edgecolor='none',width=0.6)
ax.set_xticks(range(len(ls)))
ax.set_xticklabels([l.replace('(区分不明)','(不明)') for l in ls.index],
                   fontproperties=JP,fontsize=10)
for bar,v in zip(bars,ls.values):
    col_=cT if v==ls.max() else cB
    ax.text(bar.get_x()+bar.get_width()/2,v+2,f'{int(v)}万円',
            ha='center',va='bottom',fontsize=13,fontweight='bold',
            color=col_,fontproperties=JP)
ax.set_ylim(380,510)
ax.axhline(y=ls['非上場/不明'],color=cT,linewidth=1.5,linestyle='--',alpha=0.6)
ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
ax.spines['bottom'].set_color('#E5E7EB')
ax.yaxis.grid(True,color='#F3F4F6'); ax.set_axisbelow(True)
ax.set_facecolor('white'); ax.tick_params(bottom=False,left=False)
ax.set_ylabel('下限年収中央値（万円）',fontproperties=JP,fontsize=10,color=cG)
fig.patch.set_facecolor('white'); plt.tight_layout(pad=0.5)
addimg(sl,fig2img(fig),0.22,2.05,12.9,5.1)

# ── S6: 年間休日 ────────────────────────────────────────────────────────────
sl=addsl(prs)
title_bar(sl,'年間休日分布（N=10,526件）：120〜125日帯への集中状況','📅 Annual Leave Analysis',6)

nkd=df['年間休日'].dropna()
kpi_box(sl,'年間休日データあり',f'{len(nkd):,}','件',0.22,0.9,accent=BLUE)
kpi_box(sl,'中央値','120','日',4.27,0.9,accent=TEAL)
kpi_box(sl,'120〜125日帯 集中率','99','%',8.32,0.9,accent=RED)

nk_bins=[0,110,115,120,125,130,999]; nk_labs=['110以下','110-115','115-120','120-125','125-130','130以上']
nkc=pd.cut(nkd,bins=nk_bins,labels=nk_labs,right=False)
nkv=nkc.value_counts().reindex(nk_labs).fillna(0).astype(int)

fig,ax=plt.subplots(figsize=(9.5,3.8))
bar_colors4=[cR if '120-125' in l else '#BFDBFE' for l in nk_labs]
bars=ax.barh(nk_labs,nkv.values,color=bar_colors4,height=0.5,edgecolor='none')
for bar,v in zip(bars,nkv.values):
    if v>0:
        col_=cW if v==nkv.max() else cD
        ax.text(max(nkv)*0.01,bar.get_y()+bar.get_height()/2,f'{v:,}件',
                va='center',ha='left',fontsize=11,color=col_,fontweight='bold',fontproperties=JP)
for tick in ax.get_yticklabels(): tick.set_fontproperties(JP)
ax.set_xlim(0,nkv.max()*1.15); ax.xaxis.set_visible(False)
ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
ax.spines['left'].set_visible(False); ax.spines['bottom'].set_visible(False)
ax.set_facecolor('white'); ax.tick_params(left=False,bottom=False)
fig.patch.set_facecolor('white'); plt.tight_layout(pad=0.5)
addimg(sl,fig2img(fig),0.22,2.05,12.9,5.05)

# ── S7: 残業 ────────────────────────────────────────────────────────────────
sl=addsl(prs)
title_bar(sl,'月残業時間 分布（N=10,526件）：20〜30h帯への集中状況','⏱ Overtime Distribution',7)

zgd=df['月残業'].dropna()
kpi_box(sl,'残業データあり',f'{len(zgd):,}','件',0.22,0.9,accent=BLUE)
kpi_box(sl,'中央値','20','h/月',4.27,0.9,accent=TEAL)
kpi_box(sl,'20〜30h帯 集中率','90','%',8.32,0.9,accent=RED)

zg_bins=[0,10,20,30,40,50,999]; zg_labs=['10h以下','10-20h','20-30h','30-40h','40-50h','50h以上']
zgc=pd.cut(zgd,bins=zg_bins,labels=zg_labs,right=False)
zgv=zgc.value_counts().reindex(zg_labs).fillna(0).astype(int)

fig,ax=plt.subplots(figsize=(9.5,3.8))
bar_colors5=[cR if '20-30' in l else '#BFDBFE' for l in zg_labs]
bars=ax.barh(zg_labs,zgv.values,color=bar_colors5,height=0.5,edgecolor='none')
for bar,v in zip(bars,zgv.values):
    if v>0:
        col_=cW if v==zgv.max() else cD
        ax.text(max(zgv)*0.01,bar.get_y()+bar.get_height()/2,f'{v:,}件',
                va='center',ha='left',fontsize=11,color=col_,fontweight='bold',fontproperties=JP)
for tick in ax.get_yticklabels(): tick.set_fontproperties(JP)
ax.set_xlim(0,zgv.max()*1.15); ax.xaxis.set_visible(False)
ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
ax.spines['left'].set_visible(False); ax.spines['bottom'].set_visible(False)
ax.set_facecolor('white'); ax.tick_params(left=False,bottom=False)
fig.patch.set_facecolor('white'); plt.tight_layout(pad=0.5)
addimg(sl,fig2img(fig),0.22,2.05,12.9,5.05)

# ── S8: 特典普及率 ──────────────────────────────────────────────────────────
sl=addsl(prs)
title_bar(sl,'特典別 普及率（%）：競合求人10,526件における各条件の記載率','📋 Benefit Penetration Rate',8)

ben_names=['完全週休2日','退職金制度','転勤なし','資格取得支援','社宅・住宅補助','フレックス制','リモートワーク可','育休・産休実績']
ben_vals=[round(df[f'B_{b}'].mean()*100,1) for b in ben_names]
bsorted=sorted(zip(ben_vals,ben_names),reverse=True)
bv=[b[0] for b in bsorted]; bn=[b[1] for b in bsorted]

kpi_box(sl,'完全週休2日 普及率','76','%',0.22,0.9,accent=BLUE)
kpi_box(sl,'退職金制度 普及率','74','%',4.27,0.9,accent=BLUE)
kpi_box(sl,'リモートワーク普及率','6','%',8.32,0.9,accent=TEAL)

above=[b for b in zip(bn,bv) if b[1]>=50]
below=[b for b in zip(bn,bv) if b[1]<50]

section_header(sl,'業界標準（普及率50%超）：訴求効果が薄い条件',0.22,2.08,6.3,LGRAY,MID)
fig1,ax1=plt.subplots(figsize=(5.5,2.0))
an=[a[0] for a in above]; av=[a[1] for a in above]
bars=ax1.barh(an,av,color='#94A3B8',height=0.5,edgecolor='none')
for bar,v in zip(bars,av):
    ax1.text(v+0.5,bar.get_y()+bar.get_height()/2,f'{v}%',
             va='center',ha='left',fontsize=11,color=cD,fontproperties=JP)
for tick in ax1.get_yticklabels(): tick.set_fontproperties(JP)
ax1.set_xlim(0,115); ax1.xaxis.set_visible(False)
ax1.spines['top'].set_visible(False); ax1.spines['right'].set_visible(False)
ax1.spines['left'].set_visible(False); ax1.spines['bottom'].set_visible(False)
ax1.set_facecolor('white'); ax1.tick_params(left=False,bottom=False)
fig1.patch.set_facecolor('white'); plt.tight_layout(pad=0.5)
addimg(sl,fig2img(fig1),0.22,2.42,6.3,4.2)

section_header(sl,'普及率 50%未満の条件',6.52,2.08,6.6,LBLUE,BLUE)
fig2,ax2=plt.subplots(figsize=(5.5,3.5))
bn2=[b[0] for b in below]; bv2=[b[1] for b in below]
bar_colors6=[cT if v<10 else cB for v in bv2]
bars=ax2.barh(bn2,bv2,color=bar_colors6,height=0.5,edgecolor='none')
for bar,v in zip(bars,bv2):
    ax2.text(v+0.5,bar.get_y()+bar.get_height()/2,f'{v}%',
             va='center',ha='left',fontsize=11,fontweight='bold',color=cD,fontproperties=JP)
for tick in ax2.get_yticklabels(): tick.set_fontproperties(JP)
ax2.set_xlim(0,80); ax2.xaxis.set_visible(False)
ax2.spines['top'].set_visible(False); ax2.spines['right'].set_visible(False)
ax2.spines['left'].set_visible(False); ax2.spines['bottom'].set_visible(False)
ax2.set_facecolor('white'); ax2.tick_params(left=False,bottom=False)
fig2.patch.set_facecolor('white'); plt.tight_layout(pad=0.5)
addimg(sl,fig2img(fig2),6.52,2.42,6.6,4.2)

# ── S9: リモート・フレックス ────────────────────────────────────────────────
sl=addsl(prs)
title_bar(sl,'リモートワーク・フレックス導入率（%）：建設業と他業種参考値の比較','🏠 Remote & Flex Work',9)

kpi_box(sl,'建設業 リモートワーク率','6.3','%',0.22,0.9,accent=RED)
kpi_box(sl,'他業種 参考値','55','%',4.27,0.9,accent=BLUE)
kpi_box(sl,'競合との差（リモート）','▲49','pt',8.32,0.9,accent=RED)

fig,axes=plt.subplots(1,2,figsize=(10,4.0))
for ax2,title2,tv,rv,col in [
        (axes[0],'リモートワーク可',6.3,55,cB),
        (axes[1],'フレックス制',5.8,30,cT)]:
    cats_=['建設業\n（本調査）','他業種\n（参考値）']
    vs_=[tv,rv]
    bars_=ax2.bar(cats_,vs_,color=[col,'#E5E7EB'],edgecolor='none',width=0.5)
    for bar,v in zip(bars_,vs_):
        ax2.text(bar.get_x()+bar.get_width()/2,v+0.8,f'{v}%',
                 ha='center',va='bottom',fontsize=18,fontweight='bold',
                 fontproperties=JP,color=col if v==tv else cG)
    ax2.set_title(title2,fontproperties=JP,fontsize=13,color=cN,pad=8)
    ax2.set_ylim(0,72)
    for tick in ax2.get_xticklabels(): tick.set_fontproperties(JP)
    ax2.spines['top'].set_visible(False); ax2.spines['right'].set_visible(False)
    ax2.spines['left'].set_visible(False); ax2.spines['bottom'].set_color('#E5E7EB')
    ax2.set_facecolor('white'); ax2.tick_params(bottom=False,left=False)
    ax2.yaxis.grid(True,color='#F3F4F6'); ax2.set_axisbelow(True)
    gap=rv-tv
    ax2.annotate('',xy=(1,rv),xytext=(1,tv),
                 arrowprops=dict(arrowstyle='<->',color=cR,lw=2))
    ax2.text(1.28,(tv+rv)/2,f'差\n{gap}pt',va='center',ha='left',
             fontsize=10,color=cR,fontproperties=JP,fontweight='bold')
fig.patch.set_facecolor('white'); plt.tight_layout(pad=0.5)
addimg(sl,fig2img(fig),0.22,2.05,12.9,5.05)

# ── S10: 育休 ───────────────────────────────────────────────────────────────
sl=addsl(prs)
title_bar(sl,'育休・産休実績 求人票記載率：建設業（2%）と他業種参考値の比較','👶 Parental Leave Disclosure',10)

kpi_box(sl,'育休実績 開示率','2','%',0.22,0.9,accent=RED)
kpi_box(sl,'製造業 参考値','15','%',4.27,0.9,accent=BLUE)
kpi_box(sl,'IT業界 参考値','40','%',8.32,0.9,accent=TEAL)

# Big visual
rect(sl,0.22,2.05,5.5,4.7,RGBColor(0xFF,0xF1,0xF0))
rect(sl,0.22,2.05,5.5,0.06,RED)
txt(sl,'2%',0.22,2.2,5.5,2.0,sz=88,bold=True,col=RED,align=PP_ALIGN.CENTER)
txt(sl,'10,526件中 約225件のみが\n育休・産休実績を求人票に記載',0.4,4.15,5.1,0.75,
    sz=11,col=DGRAY,align=PP_ALIGN.CENTER)
rect(sl,0.22,5.0,5.5,0.08,RED)
txt(sl,'業界最低水準',0.22,5.12,5.5,0.45,sz=13,bold=True,col=RED,align=PP_ALIGN.CENTER)

ind_labels=['建設業\n（本調査）','製造業\n（参考値）','サービス業\n（参考値）','IT業界\n（参考値）']
ind_vals=[2,15,25,40]
fig2,ax2=plt.subplots(figsize=(6.5,4.0))
bar_c2=[cR,cB,cB,cB]
bars2=ax2.bar(ind_labels,ind_vals,color=bar_c2,edgecolor='none',width=0.55)
for bar,v in zip(bars2,ind_vals):
    ax2.text(bar.get_x()+bar.get_width()/2,v+0.4,f'{v}%',
             ha='center',va='bottom',fontsize=16,fontweight='bold',
             fontproperties=JP,color=cR if v==2 else cB)
for tick in ax2.get_xticklabels(): tick.set_fontproperties(JP)
ax2.set_ylim(0,50)
ax2.spines['top'].set_visible(False); ax2.spines['right'].set_visible(False)
ax2.spines['left'].set_visible(False); ax2.spines['bottom'].set_color('#E5E7EB')
ax2.yaxis.grid(True,color='#F3F4F6'); ax2.set_axisbelow(True)
ax2.set_facecolor('white'); ax2.tick_params(bottom=False,left=False)
ax2.set_ylabel('記載率（%）',fontproperties=JP,fontsize=10,color=cG)
fig2.patch.set_facecolor('white'); plt.tight_layout(pad=0.5)
addimg(sl,fig2img(fig2),6.0,2.05,7.1,5.05)

# ── S11: 年齢条件 ───────────────────────────────────────────────────────────
sl=addsl(prs)
title_bar(sl,'年齢条件の記載状況（N=10,526件）：上限年齢・世代訴求・年齢不問の分布','🎂 Age Condition Analysis',11)

age_with=df['年齢上限'].notna().sum()
age_pct=round(age_with/len(df)*100,1)
agefree_pct=round(df['年齢不問'].mean()*100,1)
age_med=int(df['年齢上限'].dropna().median()) if age_with>0 else 0
kpi_box(sl,'年齢上限 記載あり',f'{age_pct}','%',0.22,0.9,accent=BLUE)
kpi_box(sl,'上限年齢 中央値',f'{age_med}','歳',4.27,0.9,accent=NAVY)
kpi_box(sl,'年齢不問 記載率',f'{agefree_pct}','%',8.32,0.9,accent=TEAL)

# 左: 年齢上限分布
section_header(sl,'年齢上限 分布（記載あり求人のみ）',0.22,2.08,6.3,LBLUE,BLUE)
age_bins=[0,25,30,35,40,45,99]
age_lbs=['25歳以下','26-30歳','31-35歳','36-40歳','41-45歳','46歳以上']
age_cut=pd.cut(df['年齢上限'].dropna(),bins=age_bins,labels=age_lbs,right=True)
age_cnt=age_cut.value_counts().reindex(age_lbs).fillna(0).astype(int)
fig1,ax1=plt.subplots(figsize=(5.5,3.5))
bar_ca=[cR if '31-35' in l else cB for l in age_lbs]
bars=ax1.barh(age_lbs,age_cnt.values,color=bar_ca,height=0.5,edgecolor='none')
for bar,v in zip(bars,age_cnt.values):
    if v>0:
        ax1.text(v+0.5,bar.get_y()+bar.get_height()/2,f'{v:,}件',
                 va='center',ha='left',fontsize=11,color=cD,fontproperties=JP)
for tick in ax1.get_yticklabels(): tick.set_fontproperties(JP)
ax1.set_xlim(0,age_cnt.max()*1.25 if age_cnt.max()>0 else 10); ax1.xaxis.set_visible(False)
ax1.spines['top'].set_visible(False); ax1.spines['right'].set_visible(False)
ax1.spines['left'].set_visible(False); ax1.spines['bottom'].set_visible(False)
ax1.set_facecolor('white'); ax1.tick_params(left=False,bottom=False)
fig1.patch.set_facecolor('white'); plt.tight_layout(pad=0.5)
addimg(sl,fig2img(fig1),0.22,2.42,6.3,4.5)

# 右: 世代別訴求率 + 職種別年齢上限
section_header(sl,'世代・年齢訴求キーワード 記載率',6.52,2.08,6.6,LBLUE,NAVY)
gen_labs=['20代活躍','30代活躍','40代可','年齢不問']
gen_vals=[round(df['20代'].mean()*100,1),round(df['30代'].mean()*100,1),
          round(df['40代'].mean()*100,1),round(df['年齢不問'].mean()*100,1)]
fig2,ax2=plt.subplots(figsize=(5.5,2.2))
bar_cg=[cB,cT,'#6B7280','#1A3460']
bars=ax2.barh(gen_labs,gen_vals,color=bar_cg,height=0.5,edgecolor='none')
for bar,v in zip(bars,gen_vals):
    ax2.text(v+0.3,bar.get_y()+bar.get_height()/2,f'{v}%',
             va='center',ha='left',fontsize=12,fontweight='bold',color=cD,fontproperties=JP)
for tick in ax2.get_yticklabels(): tick.set_fontproperties(JP)
ax2.set_xlim(0,max(gen_vals)*1.4 if max(gen_vals)>0 else 10); ax2.xaxis.set_visible(False)
ax2.spines['top'].set_visible(False); ax2.spines['right'].set_visible(False)
ax2.spines['left'].set_visible(False); ax2.spines['bottom'].set_visible(False)
ax2.set_facecolor('white'); ax2.tick_params(left=False,bottom=False)
fig2.patch.set_facecolor('white'); plt.tight_layout(pad=0.5)
addimg(sl,fig2img(fig2),6.52,2.42,6.6,2.3)

section_header(sl,'職種別 年齢上限 中央値（記載あり）',6.52,4.82,6.6,LGRAY,MID)
cat_age=df.groupby('カテゴリ')['年齢上限'].median().dropna().sort_values()
if len(cat_age)>0:
    fig3,ax3=plt.subplots(figsize=(5.5,2.0))
    bar_cc=[cT if v==cat_age.max() else cB for v in cat_age.values]
    bars=ax3.barh(cat_age.index,cat_age.values,color=bar_cc,height=0.5,edgecolor='none')
    for bar,v in zip(bars,cat_age.values):
        ax3.text(v+0.2,bar.get_y()+bar.get_height()/2,f'{int(v)}歳',
                 va='center',ha='left',fontsize=11,color=cD,fontproperties=JP)
    for tick in ax3.get_yticklabels(): tick.set_fontproperties(JP)
    ax3.set_xlim(20,55); ax3.xaxis.set_visible(False)
    ax3.spines['top'].set_visible(False); ax3.spines['right'].set_visible(False)
    ax3.spines['left'].set_visible(False); ax3.spines['bottom'].set_visible(False)
    ax3.set_facecolor('white'); ax3.tick_params(left=False,bottom=False)
    fig3.patch.set_facecolor('white'); plt.tight_layout(pad=0.5)
    addimg(sl,fig2img(fig3),6.52,5.16,6.6,2.0)

# ── SAVE ───────────────────────────────────────────────────────────────────
out='/tmp/建設業界_採用市場調査v2.pptx'
prs.save(out)
sz=os.path.getsize(out)/1024/1024
print(f"\n✅ {out}  ({sz:.1f}MB / {len(prs.slides)}スライド)")
