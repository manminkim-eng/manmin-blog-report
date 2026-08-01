# -*- coding: utf-8 -*-
"""MANMIN 리포트 공용 — 월별 성장 추이 패널(차트·비교표·제목검색) 생성기.
   블로그(build_month.py)와 유튜브(youtube/build_youtube.py)가 함께 사용한다.
   외부 라이브러리 없이 인라인 SVG + 순수 JS로 렌더링하며,
   데이터는 HTML 안에 직접 삽입한다(file:// 로 열어도 동작하도록 fetch 미사용)."""
import json, re

def to_num(x):
    """'3,241' -> 3241.0 / None 처리"""
    if x is None: return None
    s = str(x).strip().replace(",", "").replace("+", "").replace("%", "")
    if s in ("", "nan", "-", "—"): return None
    try: return float(s)
    except Exception: return None

def dur_to_sec(x):
    """'2m 44s' / '17s' / '1:22' -> 초"""
    if x is None: return None
    s = str(x).strip()
    if s in ("", "nan", "-"): return None
    if ":" in s:
        p = [to_num(v) or 0 for v in s.split(":")]
        return p[0]*60 + p[1] if len(p) == 2 else p[0]*3600 + p[1]*60 + p[2]
    sec = 0.0; hit = False
    for v, u in re.findall(r"(\d+(?:\.\d+)?)\s*([hms])", s):
        hit = True
        sec += float(v) * {"h": 3600, "m": 60, "s": 1}[u]
    return sec if hit else to_num(s)

CSS = """
<style>
 .trend{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:16px 18px;margin-top:18px}
 .trend .th{display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px;margin-bottom:12px}
 .trend .th h2{font-size:14.5px;font-weight:700}
 .trend .th .hint{color:var(--muted);font-size:11.5px}
 .mtabs{display:flex;gap:6px;overflow-x:auto;padding-bottom:4px;-webkit-overflow-scrolling:touch}
 .mtabs button{flex:none;font-size:12px;font-weight:600;color:var(--muted);background:var(--panel2);
   border:1px solid var(--line);border-radius:8px;padding:6px 12px;cursor:pointer;white-space:nowrap}
 .mtabs button.on{color:#0B1626;background:var(--gold);border-color:var(--gold)}
 .rtabs{display:flex;gap:6px}
 .rtabs button{font-size:11.5px;color:var(--muted);background:var(--panel2);border:1px solid var(--line);
   border-radius:7px;padding:5px 10px;cursor:pointer}
 .rtabs button.on{color:var(--gold);border-color:var(--gold)}
 .rtabs button:disabled{opacity:.35;cursor:not-allowed}
 .chartbox{position:relative;margin-top:12px}
 .chartbox svg{width:100%;height:auto;display:block}
 .tip{position:absolute;pointer-events:none;background:#0B1626;border:1px solid var(--gold);border-radius:8px;
   padding:7px 10px;font-size:11.5px;line-height:1.45;white-space:nowrap;opacity:0;transition:opacity .1s;z-index:5}
 .tip b{color:var(--gold)}
 .ttab{width:100%;border-collapse:collapse;font-size:12.5px;margin-top:12px}
 .ttab th{text-align:left;color:var(--muted);font-weight:600;font-size:11px;border-bottom:1px solid var(--line);padding:6px 8px}
 .ttab td{border-bottom:1px solid rgba(42,63,95,.5);padding:7px 8px}
 .ttab td.v{font-weight:700}
 .ttab td.d{font-size:11.5px} .up{color:#5FA98C} .dn{color:#C8452F} .fl{color:var(--muted)}
 .bar{height:8px;border-radius:3px;background:var(--gold);min-width:2px}
 .srch{margin-top:14px;border-top:1px solid var(--line);padding-top:12px}
 .srch input{width:100%;background:var(--panel2);border:1px solid var(--line);border-radius:9px;
   color:var(--ink);font-size:13px;padding:9px 12px;font-family:inherit}
 .srch input:focus{outline:none;border-color:var(--gold)}
 .srch .rs{margin-top:10px;max-height:340px;overflow-y:auto}
 .srch .row{display:flex;align-items:center;gap:10px;padding:7px 4px;border-bottom:1px solid rgba(42,63,95,.5)}
 .srch .row .t{flex:1;font-size:12.5px;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
 .srch .row .n{color:var(--gold);font-weight:700;font-size:12.5px;flex:none}
 .srch .row .sp{flex:none;display:flex;align-items:flex-end;gap:2px;height:20px}
 .srch .row .sp i{width:6px;background:var(--gold);opacity:.75;border-radius:1px;display:block}
 .srch .msg{color:var(--muted);font-size:12px;padding:8px 4px}
 @media(max-width:640px){.trend{padding:14px 12px}.ttab td.b,.ttab th.b{display:none}}
</style>"""

def panel_html(payload, title, hint, item_label):
    """payload = {metrics:[{k,l,f}], months:[...], series:{k:{month:val}},
                  items:[{t:제목, v:{month:수치}}]}"""
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    tabs = "".join(
        '<button data-i="%d"%s>%s</button>' % (i, ' class="on"' if i == 0 else "", m["l"])
        for i, m in enumerate(payload["metrics"]))
    return CSS + """
<div class="trend" id="TR">
 <div class="th"><div><h2>📈 %s</h2><div class="hint">%s</div></div>
  <div class="rtabs" id="TRr"></div></div>
 <div class="mtabs" id="TRm">%s</div>
 <div class="chartbox"><div id="TRsvg"></div><div class="tip" id="TRtip"></div></div>
 <table class="ttab"><thead><tr><th>월</th><th>값</th><th>전월 대비</th><th class="b">추이</th></tr></thead>
  <tbody id="TRtb"></tbody></table>
 <div class="srch">
  <input id="TRq" type="search" placeholder="🔍 %s 제목 검색 — 키워드를 입력하면 월별 조회수가 나옵니다">
  <div class="rs" id="TRrs"></div></div>
</div>
<script>
(function(){
 var D=%s, MS=D.months, MET=D.metrics, ITM=D.items||[];
 var mi=0, rng=Math.min(12,MS.length);
 var elM=document.getElementById('TRm'), elR=document.getElementById('TRr'),
     elS=document.getElementById('TRsvg'), elT=document.getElementById('TRtb'),
     elP=document.getElementById('TRtip'), elQ=document.getElementById('TRq'),
     elL=document.getElementById('TRrs');
 function fmt(v,f){ if(v==null) return '—';
  if(f=='pct') return (Math.round(v*10)/10)+'%%';
  if(f=='dur'){var s=Math.round(v);return s>=60?Math.floor(s/60)+'분 '+(s%%60)+'초':s+'초';}
  if(f=='f1') return (Math.round(v*10)/10).toLocaleString();
  if(f=='f2') return (Math.round(v*100)/100).toLocaleString();
  return Math.round(v).toLocaleString(); }
 function lbl(m){ return m.slice(2).replace('-','.'); }
 [3,6,12].forEach(function(n,k){ var b=document.createElement('button');
  var prev=[0,3,6][k];
  b.textContent=n+'개월'; b.disabled=(MS.length<=prev);
  b.title=b.disabled?('데이터가 '+MS.length+'개월분이라 아직 사용할 수 없습니다'):'';
  b.onclick=function(){ if(b.disabled) return; rng=n; draw(); }; b.dataset.n=n; elR.appendChild(b); });
 elM.querySelectorAll('button').forEach(function(b){
  b.onclick=function(){ mi=+b.dataset.i;
   elM.querySelectorAll('button').forEach(function(x){x.classList.remove('on');});
   b.classList.add('on'); draw(); }; });
 function draw(){
  elR.querySelectorAll('button').forEach(function(b){
   b.classList.toggle('on', +b.dataset.n===rng); });
  var M=MET[mi], ms=MS.slice(-rng), sr=D.series[M.k]||{};
  var vs=ms.map(function(m){ return sr[m]==null?null:sr[m]; });
  var mx=Math.max.apply(null,vs.filter(function(v){return v!=null;}).concat([1]));
  var W=760,H=230,PL=54,PR=14,PT=16,PB=30, iw=W-PL-PR, ih=H-PT-PB;
  var n=ms.length, bw=Math.min(46, iw/Math.max(n,1)*0.5);
  function X(i){ return PL + iw*(n===1?0.5:(i/(n-1))); }
  function Y(v){ return PT + ih - (v/mx)*ih; }
  var g='';
  for(var t=0;t<=4;t++){ var yy=PT+ih*t/4, gv=mx*(1-t/4);
   g+='<line x1="'+PL+'" y1="'+yy+'" x2="'+(W-PR)+'" y2="'+yy+'" stroke="var(--line)" stroke-width="1" opacity="'+(t===4?1:.45)+'"/>';
   g+='<text x="'+(PL-8)+'" y="'+(yy+4)+'" fill="var(--muted)" font-size="10" text-anchor="end">'+fmt(gv,M.f)+'</text>'; }
  ms.forEach(function(m,i){ var v=vs[i]; if(v==null) return;
   g+='<rect x="'+(X(i)-bw/2)+'" y="'+Y(v)+'" width="'+bw+'" height="'+(PT+ih-Y(v))+'" fill="var(--gold)" opacity=".22" rx="3"/>'; });
  var pts=[]; ms.forEach(function(m,i){ if(vs[i]!=null) pts.push(X(i)+','+Y(vs[i])); });
  if(pts.length>1) g+='<polyline points="'+pts.join(' ')+'" fill="none" stroke="var(--gold)" stroke-width="2.2" stroke-linejoin="round"/>';
  ms.forEach(function(m,i){ var v=vs[i]; if(v==null) return;
   g+='<circle cx="'+X(i)+'" cy="'+Y(v)+'" r="4.2" fill="var(--bg)" stroke="var(--gold)" stroke-width="2.2"/>';
   g+='<text x="'+X(i)+'" y="'+(H-10)+'" fill="var(--muted)" font-size="10.5" text-anchor="middle">'+lbl(m)+'</text>'; });
  ms.forEach(function(m,i){
   g+='<rect class="hz" data-i="'+i+'" x="'+(X(i)-iw/Math.max(n,1)/2)+'" y="'+PT+'" width="'+(iw/Math.max(n,1))+'" height="'+ih+'" fill="transparent"/>'; });
  elS.innerHTML='<svg viewBox="0 0 '+W+' '+H+'" preserveAspectRatio="xMidYMid meet">'+g+'</svg>';
  var box=elS.getBoundingClientRect();
  elS.querySelectorAll('.hz').forEach(function(r){
   r.addEventListener('mouseenter', function(){ show(+r.dataset.i, ms, vs, M); });
   r.addEventListener('mousemove', function(e){ move(e); });
   r.addEventListener('mouseleave', function(){ elP.style.opacity=0; }); });
  var tb='';
  for(var i=ms.length-1;i>=0;i--){ var v=vs[i], p=i>0?vs[i-1]:null, d='—', cl='fl';
   if(v!=null&&p!=null&&p!==0){ var r2=(v-p)/p*100;
    d=(r2>=0?'+':'')+(Math.round(r2*10)/10)+'%%'; cl=r2>0?'up':(r2<0?'dn':'fl'); }
   tb+='<tr><td>'+ms[i].replace('-','.')+'</td><td class="v">'+fmt(v,M.f)+'</td>'
     +'<td class="d '+cl+'">'+d+'</td><td class="b"><div class="bar" style="width:'
     +(v==null?0:Math.max(2,v/mx*100))+'%%"></div></td></tr>'; }
  elT.innerHTML=tb;
 }
 function show(i,ms,vs,M){ var v=vs[i], p=i>0?vs[i-1]:null, ex='';
  if(v!=null&&p!=null&&p!==0){ var r2=(v-p)/p*100;
   ex='<br>전월 대비 <b>'+(r2>=0?'+':'')+(Math.round(r2*10)/10)+'%%</b> ('+(v-p>=0?'+':'')+fmt(v-p,M.f)+')'; }
  elP.innerHTML=ms[i].replace('-','.')+' · '+M.l+'<br><b>'+fmt(v,M.f)+'</b>'+ex;
  elP.style.opacity=1; }
 function move(e){ var b=elS.getBoundingClientRect();
  var x=e.clientX-b.left, y=e.clientY-b.top;
  elP.style.left=Math.min(Math.max(0,x+14), b.width-elP.offsetWidth-4)+'px';
  elP.style.top=Math.max(0,y-46)+'px'; }
 function search(){ var q=(elQ.value||'').trim().toLowerCase();
  if(!q){ elL.innerHTML='<div class="msg">키워드를 입력하면 제목이 일치하는 %s의 월별 수치를 보여줍니다. (총 '+ITM.length+'건 색인)</div>'; return; }
  var hit=ITM.filter(function(it){ return it.t.toLowerCase().indexOf(q)>=0; });
  if(!hit.length){ elL.innerHTML='<div class="msg">일치하는 항목이 없습니다.</div>'; return; }
  hit.forEach(function(it){ it._s=Object.keys(it.v).reduce(function(a,k){ return a+(it.v[k]||0); },0); });
  hit.sort(function(a,b){ return b._s-a._s; });
  var top=Math.max.apply(null,hit.map(function(it){ return it._s; }).concat([1]));
  elL.innerHTML=hit.slice(0,40).map(function(it){
   var sp=MS.map(function(m){ var v=it.v[m]||0;
    return '<i style="height:'+Math.max(2,Math.round(v/top*20))+'px" title="'+m+' '+v.toLocaleString()+'"></i>'; }).join('');
   var det=MS.filter(function(m){ return it.v[m]; }).map(function(m){
    return lbl(m)+' '+it.v[m].toLocaleString(); }).join(' · ');
   return '<div class="row"><div class="sp">'+sp+'</div><div class="t" title="'
    +it.t.replace(/"/g,'&quot;')+'">'+it.t+'<br><span style="color:#8A99B5;font-size:11px">'+det+'</span></div>'
    +'<div class="n">'+it._s.toLocaleString()+'</div></div>'; }).join('')
   + (hit.length>40?'<div class="msg">상위 40건만 표시 (총 '+hit.length+'건)</div>':'');
 }
 elQ.addEventListener('input', search);
 draw(); search();
})();
</script>""" % (title, hint, tabs, item_label, data, item_label)
