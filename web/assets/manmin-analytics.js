/*! MANMIN 공통 계측 스니펫 · VER-1.0 (2026-08-09)
 *  정본 위치: manmin-blog-report/web/assets/manmin-analytics.js
 *  배포 방법: 각 WAP 저장소 assets/ 에 이 파일을 복사하고, 모든 HTML <head> 끝에 한 줄 추가
 *      <script defer src="assets/manmin-analytics.js"></script>
 *
 *  ├ GoatCounter  : 월별 정본. 보존기간 무제한 → 월간 리포트의 근거 데이터.
 *  └ Cloudflare   : 성능 보조. Core Web Vitals(LCP·INP·CLS) 제공, 조회기간 최대 30일.
 *
 *  · 중복 주입 방지 내장 — 이미 인라인 스니펫이 있는 페이지에 넣어도 이중 집계되지 않음.
 *  · localhost·file:// 에서는 자동 비활성 → 개발 중 통계 오염 없음.
 *  · 외부 의존성 없음. 두 비콘 모두 defer/async 로 렌더링을 막지 않음.
 */
(function () {
  "use strict";

  var GC_ENDPOINT = "https://manmin.goatcounter.com/count";
  var GC_SCRIPT   = "https://gc.zgo.at/count.js";
  var CF_SCRIPT   = "https://static.cloudflareinsights.com/beacon.min.js";
  var CF_TOKEN    = "e7878b8cc50d40039bb212406a3f1757";

  // ── 1. 계측 제외 조건 ───────────────────────────────────────────────
  var h = location.hostname;
  if (location.protocol === "file:") return;                       // 로컬 파일
  if (h === "localhost" || h === "127.0.0.1" || h === "" ) return; // 로컬 서버
  if (/^192\.168\.|^10\.|^172\.(1[6-9]|2\d|3[01])\./.test(h)) return; // 사내망
  if (localStorage.getItem("manmin-skip-analytics") === "1") return;  // 본인 브라우저 제외

  function has(pattern) {
    var s = document.getElementsByTagName("script");
    for (var i = 0; i < s.length; i++) {
      if (pattern.test(s[i].src || "")) return true;
    }
    return false;
  }

  function inject(attrs) {
    var el = document.createElement("script");
    for (var k in attrs) { if (attrs.hasOwnProperty(k)) el.setAttribute(k, attrs[k]); }
    (document.head || document.documentElement).appendChild(el);
  }

  // ── 2. GoatCounter (월별 정본) ──────────────────────────────────────
  if (!has(/goatcounter|gc\.zgo\.at/i)) {
    inject({ "async": "", "src": GC_SCRIPT, "data-goatcounter": GC_ENDPOINT });
  }

  // ── 3. Cloudflare Web Analytics (성능 보조) ─────────────────────────
  if (!has(/cloudflareinsights/i)) {
    inject({ "defer": "", "src": CF_SCRIPT,
             "data-cf-beacon": JSON.stringify({ token: CF_TOKEN }) });
  }
})();
