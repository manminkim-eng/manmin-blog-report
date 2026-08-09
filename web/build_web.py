# -*- coding: utf-8 -*-
"""
MANMIN 웹(WAP) 월간 방문 리포트 빌더
데이터원: GoatCounter JSON API (https://manmin.goatcounter.com/api/v0)
사용법:
  python build_web.py --month 2026-07 --period "2026.07 월간" --token <API토큰>
  python build_web.py --month 2026-07 --offline      # 이미 받아둔 data/*.json 재사용
토큰 발급: GoatCounter 우측상단 사용자메뉴 → API → 토큰 생성(읽기 권한)
표준 라이브러리만 사용 (외부 패키지 불필요)
"""
import argparse, json, os, re, sys, time, urllib.request, urllib.parse, urllib.error
from datetime import datetime, timedelta

CODE = "manmin"
API = "https://{}.goatcounter.com/api/v0".format(CODE)
HERE = os.path.dirname(os.path.abspath(__file__))

# ── 경로 → 채널 분류 규칙 (앞에서부터 먼저 맞는 것 적용) ────────────────
CHANNELS = [
    # 구 저장소명(manmin-blog)은 현행(manmin-blog-report)과 같은 채널로 병합한다.
    ("/manmin-blog-report/youtube", "유튜브 리포트",   "report"),
    ("/manmin-blog-report",         "블로그 리포트",   "report"),
    ("/manmin-blog/youtube",        "유튜브 리포트",   "report"),
    ("/manmin-blog",                "블로그 리포트",   "report"),
    ("/manmin-hub",                 "종합관리 허브",   "hub"),
    ("/KIMMANMIN",                  "엔지니어링 플랫폼", "platform"),
    ("/name-card",                  "명함 페이지",     "wap"),
]
KIND_LABEL = {"report": "리포트", "hub": "관리허브", "platform": "플랫폼", "wap": "WAP"}


def api(ep, token, **params):
    qs = urllib.parse.urlencode({k: v for k, v in params.items() if v not in (None, "")})
    url = "{}/{}{}".format(API, ep.lstrip("/"), ("?" + qs) if qs else "")
    req = urllib.request.Request(url, headers={
        "Authorization": "Bearer " + token,
        "Content-Type": "application/json",
        "User-Agent": "manmin-web-report/1.0",
    })
    # GoatCounter 레이트 리밋은 초당 4회 → 순차 호출 + 재시도
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")[:300]
            if e.code == 429 and attempt < 4:
                time.sleep(1.5)
                continue
            raise SystemExit("[API 오류] {} {} → {}\n{}".format(e.code, e.reason, url, body))
        err = data.get("error") if isinstance(data, dict) else None
        if err and "rate" in str(err).lower() and attempt < 4:
            time.sleep(1.5)
            continue
        if err:
            raise SystemExit("[API 오류] {} → {}".format(ep, err))
        time.sleep(0.3)
        return data
    raise SystemExit("[API 오류] {} → 레이트 리밋 재시도 초과".format(ep))


def month_range(month):
    y, m = (int(x) for x in month.split("-"))
    start = datetime(y, m, 1)
    end = datetime(y + (m == 12), (m % 12) + 1, 1) - timedelta(seconds=1)
    return start.strftime("%Y-%m-%dT00:00:00Z"), end.strftime("%Y-%m-%dT23:59:59Z")


def fetch_all(month, token, ddir):
    start, end = month_range(month)
    os.makedirs(ddir, exist_ok=True)
    saved = {}
    saved["total"] = api("stats/total", token, start=start, end=end)
    saved["hits"] = api("stats/hits", token, start=start, end=end, limit=100, group="day")
    for page in ("browsers", "systems", "locations", "toprefs", "sizes"):
        saved[page] = api("stats/" + page, token, start=start, end=end, limit=20)
    for k, v in saved.items():
        with open(os.path.join(ddir, k + ".json"), "w", encoding="utf-8") as f:
            json.dump(v, f, ensure_ascii=False, indent=1)
    return saved


def load_all(ddir):
    saved = {}
    for k in ("total", "hits", "browsers", "systems", "locations", "toprefs", "sizes"):
        p = os.path.join(ddir, k + ".json")
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                saved[k] = json.load(f)
    if "hits" not in saved:
        raise SystemExit("[오류] {} 에 hits.json 이 없습니다. --token 으로 먼저 수집하세요.".format(ddir))
    return saved


def norm_path(path):
    """같은 페이지가 여러 표기로 갈라지는 것을 하나로 합친다.
       /a/index.html · /a/ · /a?v=2 · /a#x  →  /a
    """
    p = (path or "").split("#")[0].split("?")[0]
    if p.endswith("/index.html"):
        p = p[:-len("/index.html")]
    elif p == "index.html":
        p = ""
    if len(p) > 1 and p.endswith("/"):
        p = p[:-1]
    return p or "/"


def merge_hits(hits):
    """정규화 경로 기준으로 방문수를 합산한다. 제목은 가장 긴 것을 채택."""
    agg = {}
    for h in hits:
        k = norm_path(h.get("path", ""))
        cur = agg.setdefault(k, {"path": k, "title": "", "count": 0, "event": h.get("event", False),
                                 "raw": []})
        cur["count"] += h.get("count", 0)
        cur["raw"].append(h.get("path", ""))
        t = h.get("title") or ""
        if len(t) > len(cur["title"]):
            cur["title"] = t
    return sorted(agg.values(), key=lambda x: -x["count"])


def classify(path):
    for pref, label, kind in CHANNELS:
        if path == pref or path.startswith(pref + "/") or path.startswith(pref + "."):
            return label, kind
    seg = [s for s in path.split("/") if s]
    if not seg:
        return "기타", "wap"
    return seg[0], "wap"


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


def fmt(n):
    return "{:,}".format(int(n or 0))


# ── 스타일 (블로그·유튜브 리포트와 동일 톤, 액센트만 엔지니어링 블루) ──
ACC = "#2FA8D5"
STYLE = """
 :root{--bg:#0B1626;--panel:#14233A;--panel2:#1B2E4A;--line:#2A3F5F;--acc:%s;--ink:#E9ECF2;--muted:#8A99B5}
 *{box-sizing:border-box;margin:0;padding:0}
 body{background:var(--bg);color:var(--ink);font-family:'Malgun Gothic','Apple SD Gothic Neo','Noto Sans KR',system-ui,sans-serif;line-height:1.5;
  background-image:linear-gradient(rgba(255,255,255,.015) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.015) 1px,transparent 1px);background-size:44px 44px}
 .wrap{max-width:1180px;margin:0 auto;padding:28px 16px 56px}
 header{display:flex;align-items:flex-end;justify-content:space-between;flex-wrap:wrap;gap:12px;border-bottom:2px solid var(--acc);padding-bottom:16px}
 .brand{display:flex;align-items:center;gap:12px} .brand img{width:38px;height:38px}
 h1{font-size:22px;font-weight:800;letter-spacing:-.5px}
 .sub{color:var(--muted);font-size:12.5px;margin-top:4px}
 .period{color:var(--acc);font-size:12.5px}
 .kpis{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin:20px 0}
 .kpi{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:13px 14px;position:relative;overflow:hidden}
 .kpi::before{content:"";position:absolute;left:0;top:0;width:4px;height:100%%;background:var(--acc)}
 .kpi .k{color:var(--muted);font-size:11px} .kpi .v{font-size:21px;font-weight:800;margin-top:3px}
 .toolbar{display:flex;gap:8px;flex-wrap:wrap;margin:14px 0 18px}
 .toolbar a{font-size:12px;color:var(--ink);background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:7px 12px;text-decoration:none}
 .toolbar a:hover{border-color:var(--acc)}
 .card{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:14px 16px;margin-bottom:14px}
 .card h2{font-size:14.5px;font-weight:700;display:flex;align-items:center;gap:8px;margin-bottom:10px}
 .card h2 .dot{width:9px;height:9px;border-radius:2px;flex:none;background:var(--acc)}
 .card h2 .cnt{color:var(--muted);font-size:11.5px;font-weight:500}
 table{width:100%%;border-collapse:collapse;font-size:12.5px}
 th{text-align:left;color:var(--muted);font-weight:600;font-size:11px;border-bottom:1px solid var(--line);padding:6px 8px}
 td{border-bottom:1px solid rgba(42,63,95,.5);padding:8px} td.nm{font-weight:600;min-width:120px}
 td.num{text-align:right;font-variant-numeric:tabular-nums} td.num b{color:var(--acc)}
 td.nt{color:var(--muted);font-size:11.5px}
 .tag{font-size:10.5px;color:var(--muted);border:1px solid var(--line);border-radius:5px;padding:1px 6px;margin-left:6px}
 .bar{height:6px;background:var(--panel2);border-radius:3px;overflow:hidden;min-width:60px}
 .bar i{display:block;height:100%%;background:var(--acc)}
 footer{color:var(--muted);font-size:11.5px;text-align:center;margin-top:24px;border-top:1px solid var(--line);padding-top:16px}
 footer a{color:var(--acc);text-decoration:none}
 .chtabs{display:flex;gap:8px;margin-top:16px;flex-wrap:wrap}
 .ct{font-size:13px;font-weight:700;color:var(--muted);background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:9px 16px;text-decoration:none}
 .ct.active{color:#0B1626;background:var(--acc);border-color:var(--acc)}
 .ct:hover{border-color:var(--acc)}
 .lead{background:linear-gradient(135deg,var(--panel2),var(--panel));border:1px solid var(--line);border-left:4px solid var(--acc);border-radius:12px;padding:15px 18px;margin-top:16px;font-size:13.5px}
 .mgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:14px;margin-top:22px}
 .mcard{display:block;background:var(--panel);border:1px solid var(--line);border-left:4px solid var(--acc);border-radius:14px;padding:18px 20px;text-decoration:none;color:var(--ink);transition:.15s}
 .mcard:hover{border-color:var(--acc);transform:translateY(-2px)}
 .mcard .mv{font-size:26px;font-weight:800;letter-spacing:-.5px}
 .mcard .mk{color:var(--muted);font-size:12px;margin-top:4px} .mcard .go{color:var(--acc);font-size:12px;margin-top:12px}
 @media(max-width:860px){.kpis{grid-template-columns:repeat(3,1fr)}td.nt{display:none}}
 @media(max-width:520px){.kpis{grid-template-columns:repeat(2,1fr)}}
""" % ACC

TABS = ('<div class="chtabs"><a class="ct" href="{r}index.html">📝 네이버 블로그</a>'
        '<a class="ct" href="{r}youtube/index.html">▶ 유튜브</a>'
        '<a class="ct active">🛠 엔지니어링 웹</a></div>')

HEAD_RAW = """<!DOCTYPE html>
<html lang="ko"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>__TITLE__</title><link rel="icon" href="__FAV__" type="image/svg+xml">
<style>""" + STYLE + """</style></head><body><div class="wrap">"""


def head(title, fav):
    """CSS 중괄호가 있어 .format() 대신 치환을 사용한다."""
    return HEAD_RAW.replace("__TITLE__", esc(title)).replace("__FAV__", fav)


def table(rows, headers, total=None):
    """rows: [(이름, 태그, 값, 비고)]"""
    mx = max([r[2] for r in rows], default=0) or 1
    out = ["<table><tr>"] + ["<th>{}</th>".format(esc(h)) for h in headers] + ["</tr>"]
    for nm, tag, val, note in rows:
        pct = (val / total * 100) if total else 0
        out.append(
            "<tr><td class='nm'>{}{}</td>"
            "<td class='num'><b>{}</b></td>"
            "<td style='width:34%'><div class='bar'><i style='width:{:.1f}%'></i></div></td>"
            "<td class='nt'>{}</td></tr>".format(
                esc(nm), ("<span class='tag'>%s</span>" % esc(tag)) if tag else "",
                fmt(val), val / mx * 100, esc(note) if note else (("%.1f%%" % pct) if total else "")))
    out.append("</table>")
    return "".join(out)


def build_month(month, period, token=None, offline=False):
    mdir = os.path.join(HERE, month)
    ddir = os.path.join(mdir, "data")
    os.makedirs(ddir, exist_ok=True)
    data = load_all(ddir) if offline else fetch_all(month, token, ddir)

    raw_hits = data["hits"].get("hits", [])
    hits = merge_hits(raw_hits)
    merged_n = len(raw_hits) - len(hits)
    total_visitors = int((data.get("total") or {}).get("total") or
                         sum(h.get("count", 0) for h in hits))

    # 채널 집계
    ch, wap = {}, {}
    for h in hits:
        label, kind = classify(h.get("path", ""))
        ch.setdefault(label, {"kind": kind, "count": 0, "pages": 0})
        ch[label]["count"] += h.get("count", 0)
        ch[label]["pages"] += 1
        if kind == "wap":
            wap.setdefault(label, 0)
            wap[label] += h.get("count", 0)

    ch_rows = [(k, KIND_LABEL[v["kind"]], v["count"], "{}개 경로".format(v["pages"]))
               for k, v in sorted(ch.items(), key=lambda x: -x[1]["count"])]
    page_rows = [(h["path"], ("병합 %d" % len(h["raw"])) if len(h["raw"]) > 1 else "",
                  h["count"], (h.get("title") or "")[:40])
                 for h in hits[:25]]

    def stat_rows(key, limit=10):
        st = (data.get(key) or {}).get("stats", []) or []
        return [(s.get("name") or "(미상)", "", s.get("count", 0), "") for s in st[:limit]]

    kpis = [
        ("총 방문자", fmt(total_visitors)),
        ("계측 경로", fmt(len(hits)) + ("" if not merged_n else " ↓{}".format(merged_n))),
        ("채널 수", fmt(len(ch))),
        ("WAP 계측", fmt(len(wap))),
        ("최다 방문", (ch_rows[0][0] if ch_rows else "-")),
    ]
    kpi_html = "".join("<div class='kpi'><div class='k'>{}</div><div class='v'>{}</div></div>"
                       .format(esc(k), esc(v)) for k, v in kpis)

    cards = [
        ("채널별 방문자", table(ch_rows, ["채널", "방문자", "", "비중"], total_visitors)),
        ("WAP 개별 순위", table(sorted([(k, "WAP", v, "") for k, v in wap.items()],
                                      key=lambda x: -x[2])[:20],
                               ["WAP", "방문자", "", "비중"], total_visitors)
         if wap else "<div class='nt' style='color:var(--muted);font-size:12.5px'>"
                     "계측 스니펫이 배포된 개별 WAP가 아직 없습니다.</div>"),
        ("인기 경로 TOP 25", table(page_rows, ["경로", "방문자", "", "제목"], total_visitors) +
         ("" if not merged_n else "<div style='color:var(--muted);font-size:11.5px;margin-top:8px'>"
          "· 동일 페이지의 다른 표기(/index.html · 끝 슬래시 · ?쿼리) {}건을 하나로 합산했습니다.</div>"
          .format(merged_n))),
        ("유입 경로", table(stat_rows("toprefs"), ["유입원", "방문자", "", "비중"], total_visitors)),
        ("브라우저", table(stat_rows("browsers"), ["브라우저", "방문자", "", "비중"], total_visitors)),
        ("운영체제", table(stat_rows("systems"), ["OS", "방문자", "", "비중"], total_visitors)),
        ("국가", table(stat_rows("locations"), ["국가", "방문자", "", "비중"], total_visitors)),
    ]
    sections = "".join(
        "<div class='card'><h2><span class='dot'></span>{}</h2>{}</div>".format(esc(t), b)
        for t, b in cards)

    body = """ <header><div class="brand"><img src="../assets/favicon.svg" alt="MANMIN"><div>
   <h1>MANMIN 엔지니어링 웹 방문 분석</h1>
   <div class="sub">manminkim-eng.github.io · GoatCounter 계측 · 건축사 김만민(#20072)</div></div></div>
   <div class="period">{period}</div></header>
 <section class="kpis">{kpis}</section>
 <div class="toolbar"><a href="../index.html">🏠 웹 리포트</a><a href="../../index.html">📝 블로그</a>
   <a href="../../youtube/index.html">▶ 유튜브</a>
   <a href="https://manminkim-eng.github.io/KIMMANMIN/" target="_blank">🛠 엔지니어링 플랫폼</a>
   <a href="https://manminkim-eng.github.io/manmin-hub/" target="_blank">📋 종합관리 허브</a></div>
 {sections}
 <footer>데이터 출처: GoatCounter API (manmin.goatcounter.com) · 원본 JSON은 data/ 폴더에 보관
  <div style="margin-top:6px"><a href="https://manminkim-eng.github.io/KIMMANMIN/">엔지니어링 플랫폼</a></div></footer>
</div></body></html>""".format(period=esc(period), kpis=kpi_html, sections=sections)
    html = head("MANMIN 웹 분석 " + month, "../assets/favicon.svg") + body

    with open(os.path.join(mdir, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print("월 인덱스 생성: {}/index.html  (방문자 {})".format(month, fmt(total_visitors)))
    return total_visitors


def build_landing():
    months = sorted([d for d in os.listdir(HERE)
                     if re.fullmatch(r"\d{4}-\d{2}", d) and
                     os.path.isdir(os.path.join(HERE, d))], reverse=True)
    cards = []
    for m in months:
        v = "-"
        p = os.path.join(HERE, m, "data", "total.json")
        if os.path.exists(p):
            try:
                with open(p, encoding="utf-8") as f:
                    v = fmt(json.load(f).get("total"))
            except Exception:
                pass
        cards.append("<a class='mcard' href='{m}/index.html'><div class='mv'>{v}</div>"
                     "<div class='mk'>{m} 방문자</div><div class='go'>상세 보기 →</div></a>"
                     .format(m=m, v=v))
    body = (""" <header><div class="brand"><img src="assets/favicon.svg" alt="MANMIN"><div>
   <h1>MANMIN 엔지니어링 웹 성과 리포트</h1>
   <div class="sub">manminkim-eng.github.io 전 저장소 월간 방문 아카이브 · 건축사 김만민(#20072)</div></div></div>
   <div class="period">총 {n}개월 색인</div></header>
 """ + TABS.format(r="../") + """
 <div class="lead"><b>엔지니어링 플랫폼·WAP·관리허브</b>의 월간 방문 지표를 GoatCounter 기준으로 색인합니다.
  Cloudflare Web Analytics는 조회 기간이 최대 30일이라 성능(Core Web Vitals) 보조 지표로만 사용합니다.</div>
 <div class="mgrid">{cards}</div>
 <footer>매월 초 갱신 · <a href="https://manminkim-eng.github.io/KIMMANMIN/">엔지니어링 플랫폼</a> ·
  <a href="https://manminkim-eng.github.io/manmin-hub/">종합관리 허브</a></footer>
</div></body></html>""").format(n=len(months), cards="".join(cards) or
                                "<div class='lead'>아직 색인된 월이 없습니다.</div>")
    html = head("MANMIN 웹 리포트", "assets/favicon.svg") + body
    with open(os.path.join(HERE, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print("랜딩 갱신: index.html ({}개월)".format(len(months)))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--month", required=True, help="YYYY-MM")
    ap.add_argument("--period", default="")
    ap.add_argument("--token", default=os.environ.get("GC_TOKEN", ""))
    ap.add_argument("--tokenfile", default=os.path.join(HERE, "token.txt"),
                    help="토큰을 담은 텍스트 파일 (기본: web/token.txt · git 제외됨)")
    ap.add_argument("--offline", action="store_true", help="이미 받아둔 data/*.json 재사용")
    a = ap.parse_args()
    if not a.token and os.path.exists(a.tokenfile):
        with open(a.tokenfile, encoding="utf-8") as f:
            a.token = f.read().strip()
        if a.token:
            print("토큰 로드: {}".format(os.path.basename(a.tokenfile)))
    if not a.offline and not a.token:
        sys.exit("[오류] 토큰이 없습니다. web/token.txt 에 저장하거나 --token 으로 넘기세요 (또는 --offline).")
    build_month(a.month, a.period or (a.month + " 월간"), a.token, a.offline)
    build_landing()
    print("완료: GitHub Desktop에서 커밋·푸시하세요.")
