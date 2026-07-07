# -*- coding: utf-8 -*-
"""
MANMIN 블로그 리포트 · 월간 인덱스 자동 생성기
사용법:
  python build_month.py --src "엑셀들어있는_폴더" --month 2026-06 --period "2026.06 월간"
동작:
  1) src의 *.xlsx 를 <repo>/<month>/data/ 로 복사
  2) <repo>/<month>/index.html 생성 (아이콘·핵심값·원본링크)
  3) <repo>/index.html (랜딩) 을 월 폴더 스캔해 자동 갱신
외부 라이브러리: pandas, openpyxl
"""
import argparse, glob, os, shutil, html, warnings, re
warnings.filterwarnings("ignore")
import pandas as pd

REPO=os.path.dirname(os.path.abspath(__file__))

def head_tags(rel):
    return ('<link rel="manifest" href="'+rel+'manifest.webmanifest">'
            '<link rel="apple-touch-icon" href="'+rel+'assets/icon-180.png">'
            '<meta name="theme-color" content="#0B1626">'
            '<meta name="mobile-web-app-capable" content="yes">'
            '<meta name="apple-mobile-web-app-capable" content="yes">'
            '<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">'
            '<meta name="apple-mobile-web-app-title" content="MANMIN 블로그">'
            '<script data-goatcounter="https://manmin.goatcounter.com/count" async src="//gc.zgo.at/count.js"></script>')

def render(tpl, **kw):
    for k,v in kw.items():
        tpl=tpl.replace("{"+k+"}", str(v))
    return tpl


# 데이터명 -> (카테고리, 종류)  종류: series/rank/dist/inflow/time
RULES={
 "조회수":("① 트래픽·방문","series"),"순방문자수":("① 트래픽·방문","series"),
 "방문횟수":("① 트래픽·방문","series"),"평균방문횟수":("① 트래픽·방문","series"),
 "재방문율":("① 트래픽·방문","series"),
 "유입분석":("② 유입·환경","inflow"),"기기별분포":("② 유입·환경","dist"),
 "국가별분포":("② 유입·환경","dist"),"시간대 분석":("② 유입·환경","time"),
 "성연령별분포":("③ 독자 프로필","genage"),
 "조회수 순위":("④ 콘텐츠 순위","rank"),"공감수 순위":("④ 콘텐츠 순위","rank"),
 "댓글수 순위":("④ 콘텐츠 순위","rank"),
 "이웃증감수":("⑤ 이웃·구독","series"),"이웃증감분석":("⑤ 이웃·구독","genage"),
 "이웃방문현황":("⑤ 이웃·구독","series"),
 "재생수":("⑥ 영상","series"),"재생수 순위":("⑥ 영상","rank"),
 "총 재생시간":("⑥ 영상","series"),"총재생시간 순위":("⑥ 영상","rank"),
 "평균 재생시간":("⑥ 영상","series"),"시청자수":("⑥ 영상","series"),
 "영상 공감수":("⑥ 영상","series"),"재생 공감수 순위":("⑥ 영상","rank"),
}
CATCOLOR={"①":"#D4A017","②":"#3E7CB1","③":"#C8452F","④":"#D4A017","⑤":"#5FA98C","⑥":"#8A99B5"}
ORDER=["① 트래픽·방문","② 유입·환경","③ 독자 프로필","④ 콘텐츠 순위","⑤ 이웃·구독","⑥ 영상"]

def read(f):
    return pd.ExcelFile(f).parse(0,header=None)
def meta(df):
    m={}
    for i in range(min(8,len(df))):
        m[str(df.iloc[i,0]).strip()]=df.iloc[i,1]
    return m

HEADER_TOKENS={"기간","순위","구분","연령별","유입경로","시간대"}
def data_region(df):
    hidx=0
    for i in range(min(13,len(df))):
        c0=str(df.iloc[i,0]).strip()
        if c0 in HEADER_TOKENS: hidx=i
    return df.iloc[hidx+1:].dropna(how="all").reset_index(drop=True)

def num(x):
    try: return float(str(x).replace(",",""))
    except: return None

def keyval(df,kind):
    d=data_region(df)
    if len(d)==0: return "데이터 없음"
    try:
        r=d.iloc[0]
        if kind=="series":
            return f"<b>{r.iloc[2]}</b>"
        if kind=="rank":
            title=str(r.iloc[1]); val=r.iloc[2]
            if title in ("nan","삭제된 영상입니다"): 
                return f"{val} · (비공개/삭제 영상)" if title=="삭제된 영상입니다" else "데이터 없음"
            t=title[:22]+("…" if len(title)>22 else "")
            return f"1위 <b>{val}</b> · {html.escape(t)}"
        if kind=="dist":
            name=r.iloc[1] if num(r.iloc[0]) is not None else r.iloc[0]
            return f"<b>{name}</b> {r.iloc[-1]}%"
        if kind=="genage":
            m_=d.iloc[0]; f_=d.iloc[1]
            return f"남 {m_.iloc[3]}% · 여 {f_.iloc[3]}%"
        if kind=="inflow":
            return f"<b>{r.iloc[0]}</b> {r.iloc[1]}%"
        if kind=="time":
            return "24시간대 조회 분포"
    except Exception:
        return "—"
    return "—"

def build_month(src, month, period):
    mdir=os.path.join(REPO,month); ddir=os.path.join(mdir,"data")
    os.makedirs(ddir,exist_ok=True)
    if os.path.abspath(src)!=os.path.abspath(ddir):
        for f in glob.glob(os.path.join(glob.escape(src),"*.xlsx")):
            shutil.copyfile(f, os.path.join(ddir,os.path.basename(f)))
    files=sorted(glob.glob(os.path.join(glob.escape(ddir),"*.xlsx")))
    cats={c:[] for c in ORDER}; cats["기타"]=[]
    kpi={}
    for f in files:
        df=read(f); m=meta(df); name=str(m.get("데이터명","")).strip()
        cat,kind=RULES.get(name,("기타","series"))
        kv=keyval(df,kind)
        per=str(m.get("데이터 기간","")).strip()
        cats.setdefault(cat,[]).append((name,kv,per,os.path.basename(f)))
        # KPI 수집 (헤더행 자동탐지 후 최신월 col2 / 분포 top pct)
        try:
            d=data_region(df)
            if len(d):
                if name=="조회수": kpi["조회수"]=d.iloc[0,2]
                if name=="순방문자수": kpi["순방문자"]=d.iloc[0,2]
                if name=="방문횟수": kpi["방문횟수"]=d.iloc[0,2]
                if name=="이웃증감수": kpi["이웃증가"]=d.iloc[0,2]
                if name=="기기별분포": kpi["모바일"]=str(d.iloc[0,-1])+"%"
                if name=="국가별분포": kpi["국내"]=str(d.iloc[0,-1])+"%"
        except Exception: pass

    # sections html
    sec=""
    for cat in ORDER+["기타"]:
        items=cats.get(cat) or []
        if not items: continue
        color=CATCOLOR.get(cat[0],"#8A99B5")
        trs=""
        for name,kv,per,fname in items:
            trs+=(f'<tr><td class="nm">{html.escape(name)}</td>'
                  f'<td class="kv">{kv}</td>'
                  f'<td class="nt">{html.escape(per)}</td>'
                  f'<td class="dl"><a href="data/{html.escape(fname)}" download>xlsx ↓</a></td></tr>')
        sec+=(f'<div class="card"><h2><span class="dot" style="background:{color}"></span>{html.escape(cat)}'
              f' <span class="cnt">{len(items)}종</span></h2>'
              f'<table><thead><tr><th>데이터</th><th>핵심값</th><th>기간</th><th>파일</th></tr></thead>'
              f'<tbody>{trs}</tbody></table></div>')

    def g(k,d="—"): 
        v=kpi.get(k); return d if v is None else v
    kpihtml=f"""
     <div class="kpi"><div class="k">조회수(월)</div><div class="v">{g('조회수')}</div></div>
     <div class="kpi"><div class="k">순방문자(월)</div><div class="v">{g('순방문자')}</div></div>
     <div class="kpi"><div class="k">방문횟수</div><div class="v">{g('방문횟수')}</div></div>
     <div class="kpi"><div class="k">이웃 증가</div><div class="v">{g('이웃증가')}</div></div>
     <div class="kpi"><div class="k">모바일</div><div class="v">{g('모바일')}</div></div>
     <div class="kpi"><div class="k">국내</div><div class="v">{g('국내')}</div></div>"""

    dash = 'dashboard.html' if os.path.exists(os.path.join(mdir,"dashboard.html")) else None
    dashbtn = f'<a href="dashboard.html">📊 성과 대시보드</a>' if dash else ''
    total=sum(len(v) for v in cats.values())
    doc=render(PAGE, title="MANMIN 블로그 분석 · "+period, period=period, total=str(total),
                    kpis=kpihtml, sections=sec, dashbtn=dashbtn, fav="../assets/favicon.svg", pwa=head_tags("../"))
    open(os.path.join(mdir,"index.html"),"w",encoding="utf-8").write(doc)
    print(f"[OK] {month}/index.html  ({total}종)")
    return total

def build_landing():
    months=sorted([d for d in os.listdir(REPO) if re.match(r"^\d{4}-\d{2}$",d)], reverse=True)
    cards=""
    for m in months:
        idx=os.path.join(REPO,m,"index.html")
        n=len(glob.glob(os.path.join(glob.escape(os.path.join(REPO,m,"data")),"*.xlsx")))
        y,mo=m.split("-")
        cards+=(f'<a class="mcard" href="{m}/index.html"><div class="mv">{y}.{mo}</div>'
                f'<div class="mk">월간 분석 · 지표 {n}종</div><div class="go">열기 →</div></a>')
    doc=render(LANDING, cards=cards or '<p style="color:#8A99B5">아직 등록된 월간 리포트가 없습니다.</p>',
                       n=str(len(months)), fav="assets/favicon.svg", pwa=head_tags(""))
    open(os.path.join(REPO,"index.html"),"w",encoding="utf-8").write(doc)
    print(f"[OK] landing index.html  ({len(months)}개월)")

# ---------- 템플릿 ----------
STYLE="""
 :root{--bg:#0B1626;--panel:#14233A;--panel2:#1B2E4A;--line:#2A3F5F;--gold:#D4A017;--ink:#E9ECF2;--muted:#8A99B5}
 *{box-sizing:border-box;margin:0;padding:0}
 body{background:var(--bg);color:var(--ink);font-family:'Malgun Gothic','Apple SD Gothic Neo','Noto Sans KR',system-ui,sans-serif;line-height:1.5;
  background-image:linear-gradient(rgba(255,255,255,.015) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.015) 1px,transparent 1px);background-size:44px 44px}
 .wrap{max-width:1180px;margin:0 auto;padding:28px 16px 56px}
 header{display:flex;align-items:flex-end;justify-content:space-between;flex-wrap:wrap;gap:12px;border-bottom:2px solid var(--gold);padding-bottom:16px}
 .brand{display:flex;align-items:center;gap:12px} .brand img{width:38px;height:38px}
 h1{font-size:22px;font-weight:800;letter-spacing:-.5px}
 .sub{color:var(--muted);font-size:12.5px;margin-top:4px}
 .period{color:var(--gold);font-size:12.5px}
 .kpis{display:grid;grid-template-columns:repeat(6,1fr);gap:10px;margin:20px 0}
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
 td.kv b{color:var(--gold)} td.nt{color:var(--muted);font-size:11.5px}
 td.dl a{color:var(--gold);text-decoration:none;font-size:11.5px;border:1px solid var(--line);border-radius:6px;padding:3px 8px;white-space:nowrap}
 td.dl a:hover{border-color:var(--gold)}
 footer{color:var(--muted);font-size:11.5px;text-align:center;margin-top:24px;border-top:1px solid var(--line);padding-top:16px}
 footer a{color:var(--gold);text-decoration:none}
 @media(max-width:860px){.kpis{grid-template-columns:repeat(3,1fr)}td.nt{display:none}th:nth-child(3){display:none}}
 @media(max-width:520px){.kpis{grid-template-columns:repeat(2,1fr)}}
"""

PAGE="""<!DOCTYPE html>
<html lang="ko"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title><link rel="icon" href="{fav}" type="image/svg+xml">{pwa}
<style>"""+STYLE+"""</style></head><body><div class="wrap">
 <header><div class="brand"><img src="{fav}" alt="MANMIN"><div>
   <h1>MANMIN 블로그 분석 자료 인덱스</h1>
   <div class="sub">네이버 블로그 manmin72 · 지표 {total}종 통합 색인 · 건축사 김만민(#20072)</div></div></div>
   <div class="period">{period}</div></header>
 <section class="kpis">{kpis}</section>
 <div class="toolbar"><a href="../index.html">🏠 전체 리포트</a>{dashbtn}
   <a href="https://blog.naver.com/manmin72" target="_blank">✍ 네이버 블로그</a>
   <a href="https://manminkim-eng.github.io/KIMMANMIN/" target="_blank">🛠 엔지니어링 플랫폼</a>
   <a href="https://www.youtube.com/@김만민-x8p" target="_blank">▶ YouTube</a></div>
 {sections}
 <footer>MANMIN 답사·엔지니어링 · 데이터 출처: 네이버 블로그 통계 · ‘xlsx ↓’ = 원본 파일
  <div style="margin-top:6px"><a href="https://blog.naver.com/manmin72">blog.naver.com/manmin72</a></div></footer>
</div></body></html>"""

LANDING="""<!DOCTYPE html>
<html lang="ko"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MANMIN 블로그 리포트</title><link rel="icon" href="{fav}" type="image/svg+xml">{pwa}
<style>"""+STYLE+"""
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
   <h1>MANMIN 블로그 성과 리포트</h1>
   <div class="sub">네이버 블로그 manmin72 월간 분석 아카이브 · 건축사 김만민(#20072)</div></div></div>
   <div class="period">총 {n}개월 색인</div></header>
 <div class="chtabs"><a class="ct active">📝 네이버 블로그</a><a class="ct" href="youtube/index.html">▶ 유튜브</a></div>
 <div class="lead"><b>MANMIN 답사·엔지니어링</b> 블로그의 월간 방문·유입·콘텐츠·이웃 지표를 매월 색인합니다. 아래 월을 선택하면 해당 월 상세 인덱스로 이동합니다.</div>
 <div class="mgrid">{cards}</div>
 <footer>매월 초 갱신 · <a href="https://blog.naver.com/manmin72">blog.naver.com/manmin72</a> ·
  <a href="https://manminkim-eng.github.io/KIMMANMIN/">엔지니어링 플랫폼</a></footer>
</div></body></html>"""

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--src",required=True); ap.add_argument("--month",required=True)
    ap.add_argument("--period",default="")
    a=ap.parse_args()
    build_month(a.src, a.month, a.period or a.month+" 월간")
    build_landing()
    print("완료: GitHub Desktop에서 커밋·푸시하세요.")
