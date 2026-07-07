# MANMIN 블로그 성과 리포트 (manmin-blog-report)

네이버 블로그 **manmin72**(건축사 김만민)의 월간 통계를 색인·시각화하는 GitHub Pages 사이트입니다.
매월 초 네이버 블로그 통계 엑셀을 내려받아 업로드하면, 월별 인덱스와 대시보드가 자동 생성됩니다.

## 폴더 구조
```
manmin-blog-report/
├── index.html          ← 랜딩(월 목록, 자동 갱신)
├── assets/favicon.svg  ← MANMIN 아이콘
├── build_month.py      ← 월간 자동 생성 스크립트
├── 2026-06/
│   ├── index.html      ← 그 달 데이터 인덱스(24종 색인)
│   ├── dashboard.html  ← 성과 대시보드(차트)
│   └── data/*.xlsx     ← 네이버 통계 원본
└── README.md
```

## 매월 작업 순서 (약 3분)
1. 네이버 블로그 → 통계 → 각 지표 **엑셀 다운로드**
2. Claude(Cowork)에게 엑셀을 업로드하고 "이번 달 블로그 인덱스 만들어줘"라고 요청
   - 또는 직접: `python build_month.py --src "엑셀폴더" --month 2026-07 --period "2026.07 월간"`
3. **GitHub Desktop** 실행 → 변경사항 확인 → Commit → **Push origin**
4. 1~2분 후 `https://manminkim-eng.github.io/manmin-blog-report/` 에 반영

## GitHub 최초 설정 (한 번만)
1. GitHub Desktop 설치·로그인 (github.com 계정)
2. File → Add local repository → 이 폴더 선택 → "create a repository" → 이름 `manmin-blog-report`
3. Publish repository (Public 체크 — Pages는 공개 저장소 필요)
4. github.com → 저장소 → Settings → Pages → Source: `main` / `/(root)` → Save
5. 몇 분 후 `https://<계정>.github.io/manmin-blog-report/` 공개

## 데이터
네이버 블로그 통계 지표 다운로드(월간). 원본 xlsx는 각 달 `data/` 폴더에 보관됩니다.
