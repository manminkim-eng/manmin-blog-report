# -*- coding: utf-8 -*-
"""
MANMIN 유튜브 리포트 · 월간 인덱스 자동 생성기
사용법:
  python build_youtube.py --src "CSV들어있는_폴더" --month 2026-06 --period "2026.06 월간"
동작:
  1) src 하위의 카테고리 폴더별 YouTube Studio CSV 를 <repo>/<month>/data/ 로 복사
  2) <repo>/<month>/index.html 생성 (아이콘·핵심값·원본링크)
  3) <repo>/index.html (랜딩) 을 월 폴더 스캔해 자동 갱신
외부 라이브러리: pandas
CSV 구조: YouTube 스튜디오 > 분석 > 고급 모드 > (탭 선택) > 내보내기(.csv)
  ZIP 압축 해제 시 'Chart data.csv' / 'Table data.csv' / 'Totals.csv' 3종.
  각 탭(개요/콘텐츠/트래픽소스/지역/연령및성별/기기/구독상태)을 같은 이름의
  하위 폴더에 넣어 두면 카테고리로 자동 인식.
"""
import argparse, glob, os, sys, shutil, html, warnings, re
warnings.filterwarnings("ignore")
import pandas as pd

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(REPO))
import trendkit

CATS = {
    "개요":       ("① 채널 개요",     "overview"),
    "콘텐츠":     ("② 영상 순위",     "rank"),
    "트래픽소스": ("③ 트래픽 소스",   "dist"),
    "지역":       ("④ 시청 지역",     "dist"),
    "연령및성별": ("⑤ 시청자 프로필", "genage"),
    "기기":       ("⑥ 기기 유형",     "dist"),
    "구독상태":   ("⑦ 구독 상태",     "dist"),
}
CATCOLOR = {"①": "#E23B2E", "②": "#E23B2E", "③": "#3E7CB1", "④": "#5FA98C",
            "⑤": "#C8452F", "⑥": "#8A99B5", "⑦": "#D4A017"}
ORDER = ["① 채널 개요", "② 영상 순위", "③ 트래픽 소스", "④ 시청 지역",
         "⑤ 시청자 프로필", "⑥ 기기 유형", "⑦ 구독 상태"]

COL_VIEWS = ["조회수", "views"]
COL_WATCH = ["시청 시간", "시청시간", "watch time"]
COL_SUBS  = ["구독자", "subscribers"]


def find_col(cols, keys):
    for c in cols:
        cl = str(c).strip().lower()
        for k in keys:
            if k.lower() in cl:
                return c
    return None


def read_csv(f):
    for enc in ("utf-8-sig", "utf-8", "cp949"):
        try:
            return pd.read_csv(f, encoding=enc)
        except Exception:
            continue
    return pd.read_csv(f, encoding="utf-8", engine="python", on_bad_lines="skip")


def classify(fname):
    n = os.path.basename(fname).lower()
    if "total" in n or "합계" in n:
        return "totals"
    if "table" in n or "표" in n:
        return "table"
    if "chart" in n or "차트" in n:
        return "chart"
    return "other"


def fmt(x):
    s = str(x).strip()
    try:
        f = float(s.replace(",", ""))
        if f == int(f):
            return f"{int(f):,}"
        return f"{f:,.1f}"
    except Exception:
        return s


def head_tags(rel):
    return ('<link rel="manifest" href="' + rel + 'manifest.webmanifest">'
            '<link rel="apple-touch-icon" href="' + rel + 'assets/icon-180.png">'
            '<meta name="theme-color" content="#0B1626">'
            '<meta name="mobile-web-app-capable" content="yes">'
            '<meta name="apple-mobile-web-app-capable" content="yes">'
            '<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">'
            '<meta name="apple-mobile-web-app-title" content="MANMIN YouTube">'
            '<script data-goatcounter="https://manmin.goatcounter.com/count" async src="//gc.zgo.at/count.js"></script>')


def render(tpl, **kw):
    for k, v in kw.items():
        tpl = tpl.replace("{" + k + "}", str(v))
    return tpl


def summarize(catkind, files):
    kpi = {}
    kv = "데이터 없음"
    totals = next((f for f in files if classify(f) == "totals"), None)
    table = next((f for f in files if classify(f) == "table"), None)
    chart = next((f for f in files if classify(f) == "chart"), None)
    src = totals or table or chart or (files[0] if files else None)
    if src is None:
        return kv, kpi
    try:
        df = read_csv(src)
        cols = list(df.columns)
        cv, cw, cs = find_col(cols, COL_VIEWS), find_col(cols, COL_WATCH), find_col(cols, COL_SUBS)

        if catkind == "overview":
            row = df.iloc[0] if len(df) else None
            if row is not None:
                if cv: kpi["조회수"] = fmt(row[cv])
                if cw: kpi["시청시간"] = fmt(row[cw])
                if cs: kpi["구독자증감"] = fmt(row[cs])
            parts = []
            if cv and "조회수" in kpi: parts.append(f"조회수 <b>{kpi['조회수']}</b>")
            if cw and "시청시간" in kpi: parts.append(f"시청 {kpi['시청시간']}h")
            kv = " · ".join(parts) if parts else "개요 데이터"
            return kv, kpi

        if catkind == "rank":
            if table:
                df = read_csv(table)
                cols = list(df.columns)
                cv = find_col(cols, COL_VIEWS)
                d = df[~df.iloc[:, 0].astype(str).str.strip().str.lower().isin(["total", "합계"])]
                if len(d):
                    title = str(d.iloc[0, 0])[:26]
                    val = d.iloc[0][cv] if cv else d.iloc[0, 1]
                    kv = f"1위 <b>{fmt(val)}</b> · {html.escape(title)}"
            return kv, kpi

        if catkind == "genage":
            if table:
                df = read_csv(table)
            male = female = None
            for _, r in df.iterrows():
                c0 = str(r.iloc[0])
                if "남" in c0 and male is None: male = r.iloc[-1]
                if "여" in c0 and female is None: female = r.iloc[-1]
            if male is not None or female is not None:
                kv = f"남 {fmt(male)}% · 여 {fmt(female)}%"
            else:
                kv = f"{len(df)}개 구간 분포"
            return kv, kpi

        if catkind == "dist":
            if table:
                df = read_csv(table)
            cols = list(df.columns)
            cv = find_col(cols, COL_VIEWS)
            valcol = cv or (cols[1] if len(cols) > 1 else cols[0])
            ispct = ("%" in str(valcol)) or ("비율" in str(valcol))
            d = df[~df.iloc[:, 0].astype(str).str.strip().str.lower().isin(["total", "합계"])]
            if len(d):
                name = str(d.iloc[0, 0])[:20]
                val = d.iloc[0][valcol]
                kv = f"<b>{html.escape(name)}</b> · {fmt(val)}{'%' if ispct else ''}"
            return kv, kpi
    except Exception:
        return "—", kpi
    return kv, kpi


def build_month(src, month, period):
    mdir = os.path.join(REPO, month)
    ddir = os.path.join(mdir, "data")
    os.makedirs(ddir, exist_ok=True)

    cats = {c: [] for c in ORDER}
    kpi_all = {}

    for folder, (catname, kind) in CATS.items():
        srcf = os.path.join(src, folder)
        if not os.path.isdir(srcf):
            srcf = os.path.join(ddir, folder)
        if not os.path.isdir(srcf):
            continue
        dst = os.path.join(ddir, folder)
        os.makedirs(dst, exist_ok=True)
        files = []
        for f in glob.glob(os.path.join(glob.escape(srcf), "*.csv")):
            b = os.path.basename(f)
            tgt = os.path.join(dst, b)
            if os.path.abspath(f) != os.path.abspath(tgt):
                shutil.copyfile(f, tgt)
            files.append(tgt)
        if not files:
            continue
        kv, kpi = summarize(kind, files)
        kpi_all.update(kpi)
        cats[catname].append((catname, kv, folder, files))

    sec = ""
    for cat in ORDER:
        items = cats.get(cat) or []
        if not items:
            continue
        color = CATCOLOR.get(cat[0], "#8A99B5")
        trs = ""
        for name, kv, folder, files in items:
            dls = " ".join(
                f'<a href="data/{html.escape(folder)}/{html.escape(os.path.basename(f))}" download>{html.escape(os.path.basename(f).split(".")[0][:10])} ↓</a>'
                for f in files)
            trs += (f'<tr><td class="nm">{html.escape(name)}</td>'
                    f'<td class="kv">{kv}</td>'
                    f'<td class="dl">{dls}</td></tr>')
        sec += (f'<div class="card"><h2><span class="dot" style="background:{color}"></span>{html.escape(cat)}'
                f' <span class="cnt">{len(items)}종</span></h2>'
                f'<table><thead><tr><th>지표</th><th>핵심값</th><th>원본 CSV</th></tr></thead>'
                f'<tbody>{trs}</tbody></table></div>')

    def g(k, d="—"):
        v = kpi_all.get(k)
        return d if v is None else v

    kpihtml = f"""
     <div class="kpi"><div class="k">조회수(월)</div><div class="v">{g('조회수')}</div></div>
     <div class="kpi"><div class="k">시청시간(h)</div><div class="v">{g('시청시간')}</div></div>
     <div class="kpi"><div class="k">구독자 증감</div><div class="v">{g('구독자증감')}</div></div>"""

    total = sum(len(v) for v in cats.values())
    doc = render(PAGE, title="MANMIN 유튜브 분석 · " + period, period=period, total=str(total),
                 kpis=kpihtml, sections=sec or '<p style="color:#8A99B5">등록된 데이터가 없습니다. data/ 하위에 카테고리 폴더(개요/콘텐츠/…)를 넣어주세요.</p>',
                 fav="../assets/favicon.svg", pwa=head_tags("../"))
    open(os.path.join(mdir, "index.html"), "w", encoding="utf-8").write(doc)
    print(f"[OK] {month}/index.html  ({total}개 카테고리)")
    return total



# ---------- 월별 성장 추이 데이터 ----------
YT_METRICS=[
 {"k":"조회수","l":"조회수","f":"int"},
 {"k":"시청시간","l":"시청시간(h)","f":"f1"},
 {"k":"구독자","l":"구독자 증감","f":"int"},
 {"k":"노출수","l":"노출수","f":"int"},
 {"k":"CTR","l":"노출 클릭률","f":"pct"},
]
_YT_COLS=[("조회수",0),("시청시간",1),("구독자",2),("노출수",3),("CTR",4)]

def _read_csv(path):
    for enc in ("utf-8-sig","cp949","utf-8"):
        try: return pd.read_csv(path, encoding=enc)
        except Exception: continue
    return None

def collect_trend():
    """월별 개요/Totals.csv 에서 KPI 추이를, 콘텐츠/Table data.csv 에서 영상별 월간 조회수를 모은다."""
    months=sorted([d for d in os.listdir(REPO) if re.match(r"^\d{4}-\d{2}$",d)])
    series={k:{} for k,_ in _YT_COLS}
    items={}
    for mo in months:
        tot=os.path.join(REPO,mo,"data","개요","Totals.csv")
        if os.path.exists(tot):
            df=_read_csv(tot)
            if df is not None and len(df):
                r=df.iloc[0]
                for key,ci in _YT_COLS:
                    if ci < len(r):
                        v=trendkit.to_num(r.iloc[ci])
                        if v is not None: series[key][mo]=v
        con=os.path.join(REPO,mo,"data","콘텐츠","Table data.csv")
        if os.path.exists(con):
            df=_read_csv(con)
            if df is not None:
                for _,r in df.iterrows():
                    t=str(r.iloc[0]).strip()
                    if not t or t in ("nan","합계","Total"): continue
                    v=trendkit.to_num(r.iloc[1] if len(r)>1 else None)
                    if v is None: continue
                    items.setdefault(t,{})[mo]=int(v)
    allm=sorted({m for k in series for m in series[k]})
    if not allm: return None
    return {"metrics":YT_METRICS,"months":allm,"series":series,
            "items":[{"t":t,"v":v} for t,v in items.items()]}

def build_landing():
    months = sorted([d for d in os.listdir(REPO) if re.match(r"^\d{4}-\d{2}$", d)], reverse=True)
    cards = ""
    for m in months:
        ddir = os.path.join(REPO, m, "data")
        n = len([d for d in glob.glob(os.path.join(glob.escape(ddir), "*")) if os.path.isdir(d)]) if os.path.isdir(ddir) else 0
        y, mo = m.split("-")
        cards += (f'<a class="mcard" href="{m}/index.html"><div class="mv">{y}.{mo}</div>'
                  f'<div class="mk">월간 분석 · 카테고리 {n}종</div><div class="go">열기 →</div></a>')
    tr = collect_trend()
    trend = trendkit.panel_html(tr, "월별 성장 추이",
             "지표 탭·기간을 바꿔 보세요. 차트에 마우스를 올리면 전월 대비 증감이 나옵니다.",
             "영상") if tr else ""
    doc = render(LANDING, cards=cards or '<p style="color:#8A99B5">아직 등록된 월간 리포트가 없습니다.</p>',
                 n=str(len(months)), fav="assets/favicon.svg", pwa=head_tags(""), trend=trend)
    open(os.path.join(REPO, "index.html"), "w", encoding="utf-8").write(doc)
    print(f"[OK] landing index.html  ({len(months)}개월)")


STYLE = """
 :root{--bg:#0B1626;--panel:#14233A;--panel2:#1B2E4A;--line:#2A3F5F;--gold:#E23B2E;--ink:#E9ECF2;--muted:#8A99B5}
 *{box-sizing:border-box;margin:0;padding:0}
 body{background:var(--bg);color:var(--ink);font-family:'Malgun Gothic','Apple SD Gothic Neo','Noto Sans KR',system-ui,sans-serif;line-height:1.5;
  background-image:linear-gradient(rgba(255,255,255,.015) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.015) 1px,transparent 1px);background-size:44px 44px}
 .wrap{max-width:1180px;margin:0 auto;padding:28px 16px 56px}
 header{display:flex;align-items:flex-end;justify-content:space-between;flex-wrap:wrap;gap:12px;border-bottom:2px solid var(--gold);padding-bottom:16px}
 .brand{display:flex;align-items:center;gap:12px} .brand img{width:38px;height:38px}
 h1{font-size:22px;font-weight:800;letter-spacing:-.5px}
 .sub{color:var(--muted);font-size:12.5px;margin-top:4px}
 .period{color:var(--gold);font-size:12.5px}
 .kpis{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:20px 0}
 .kpi{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:13px 14px;position:relative;overflow:hidden}
 .kpi::before{content:"";position:absolute;left:0;top:0;width:4px;height:100%;background:var(--gold)}
 .kpi .k{color:var(--muted);font-size:11px} .kpi .v{font-size:21px;font-weight:800;margin-top:3px}
 .toolbar{display:flex;gap:8px;flex-wrap:wrap;margin:14px 0 18px}
 .toolbar a{font-size:12px;color:var(--ink);background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:7px 12px;text-decoration:none}
 .toolbar a:hover{border-color:var(--gold)}
 .card{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:14px 16px;margin-bottom:14px}
 .card h2{font-size:14.5px;font-weight:700;display:flex;align-items:center;gap:8px;margin-bottom:10px}
 .card h2 .dot{width:9px;height:9px;border-radius:2px;flex:none} .card h2 .cnt{color:var(--muted);font-size:11.5px;font-weight:500}
 table{width:100%;border-collapse:collapse;font-size:12.5px}
 th{text-align:left;color:var(--muted);font-weight:600;font-size:11px;border-bottom:1px solid var(--line);padding:6px 8px}
 td{border-bottom:1px solid rgba(42,63,95,.5);padding:8px} td.nm{font-weight:600;min-width:120px}
 td.kv b{color:var(--gold)}
 td.dl a{color:var(--gold);text-decoration:none;font-size:11.5px;border:1px solid var(--line);border-radius:6px;padding:3px 8px;white-space:nowrap;margin-right:4px}
 td.dl a:hover{border-color:var(--gold)}
 footer{color:var(--muted);font-size:11.5px;text-align:center;margin-top:24px;border-top:1px solid var(--line);padding-top:16px}
 footer a{color:var(--gold);text-decoration:none}
 @media(max-width:520px){.kpis{grid-template-columns:repeat(1,1fr)}}
"""

PAGE = """<!DOCTYPE html>
<html lang="ko"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title><link rel="icon" href="{fav}" type="image/svg+xml">{pwa}
<style>""" + STYLE + """</style></head><body><div class="wrap">
 <header><div class="brand"><img src="{fav}" alt="MANMIN"><div>
   <h1>MANMIN 유튜브 분석 자료 인덱스</h1>
   <div class="sub">YouTube 채널 @김만민 · 카테고리 {total}종 통합 색인 · 건축사 김만민(#20072)</div></div></div>
   <div class="period">{period}</div></header>
 <section class="kpis">{kpis}</section>
 <div class="toolbar"><a href="../index.html">🏠 전체 리포트</a>
   <a href="https://www.youtube.com/@김만민-x8p" target="_blank">▶ YouTube 채널</a>
   <a href="https://studio.youtube.com" target="_blank">🎛 YouTube 스튜디오</a>
   <a href="https://blog.naver.com/manmin72" target="_blank">✍ 네이버 블로그</a>
   <a href="https://manminkim-eng.github.io/KIMMANMIN/" target="_blank">🛠 엔지니어링 플랫폼</a></div>
 {sections}
 <footer>MANMIN 답사·엔지니어링 · 데이터 출처: YouTube 스튜디오 분석 · ‘CSV ↓’ = 원본 파일
  <div style="margin-top:6px"><a href="https://www.youtube.com/@김만민-x8p">youtube.com/@김만민</a></div></footer>
</div></body></html>"""

LANDING = """<!DOCTYPE html>
<html lang="ko"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MANMIN 유튜브 리포트</title><link rel="icon" href="{fav}" type="image/svg+xml">{pwa}
<style>""" + STYLE + """
 .mgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:14px;margin-top:22px}
 .mcard{display:block;background:var(--panel);border:1px solid var(--line);border-left:4px solid var(--gold);border-radius:14px;padding:18px 20px;text-decoration:none;color:var(--ink);transition:.15s}
 .mcard:hover{border-color:var(--gold);transform:translateY(-2px)}
 .mcard .mv{font-size:26px;font-weight:800;letter-spacing:-.5px}
 .mcard .mk{color:var(--muted);font-size:12px;margin-top:4px} .mcard .go{color:var(--gold);font-size:12px;margin-top:12px}
 .lead{background:linear-gradient(135deg,var(--panel2),var(--panel));border:1px solid var(--line);border-left:4px solid var(--gold);border-radius:12px;padding:15px 18px;margin-top:16px;font-size:13.5px}
 .chtabs{display:flex;gap:8px;margin-top:16px;flex-wrap:wrap}
 .ct{font-size:13px;font-weight:700;color:var(--muted);background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:9px 16px;text-decoration:none}
 .ct.active{color:#0B1626;background:var(--gold);border-color:var(--gold)}
 .ct:hover{border-color:var(--gold)}
</style></head><body><div class="wrap">
 <header><div class="brand"><img src="{fav}" alt="MANMIN"><div>
   <h1>MANMIN 유튜브 성과 리포트</h1>
   <div class="sub">YouTube 채널 @김만민 월간 분석 아카이브 · 건축사 김만민(#20072)</div></div></div>
   <div class="period">총 {n}개월 색인</div></header>
 <div class="chtabs"><a class="ct" href="../index.html">📝 네이버 블로그</a><a class="ct active">▶ 유튜브</a></div>
 <div class="lead"><b>MANMIN 답사·엔지니어링</b> 유튜브 채널의 월간 조회수·시청시간·구독자·트래픽·시청자 지표를 매월 색인합니다. 아래 월을 선택하면 해당 월 상세 인덱스로 이동합니다.</div>
 {trend}
 <div class="mgrid">{cards}</div>
 <footer>매월 초 갱신 · <a href="https://www.youtube.com/@김만민-x8p">youtube.com/@김만민</a> ·
  <a href="https://manminkim-eng.github.io/KIMMANMIN/">엔지니어링 플랫폼</a></footer>
</div></body></html>"""

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--month", required=True)
    ap.add_argument("--period", default="")
    a = ap.parse_args()
    build_month(a.src, a.month, a.period or a.month + " 월간")
    build_landing()
    print("완료: GitHub Desktop에서 커밋·푸시하세요.")
