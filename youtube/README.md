# MANMIN 유튜브 성과 리포트 (manmin-youtube-report)

YouTube 채널 **@김만민**(건축사 김만민)의 월간 통계를 색인·시각화하는 GitHub Pages 사이트입니다.
네이버 블로그 리포트(`manmin-blog-report`)와 동일한 운영 방식입니다. 매월 초 YouTube 스튜디오에서
CSV를 내려받아 카테고리 폴더에 넣고 스크립트를 돌린 뒤 GitHub Desktop으로 푸시하면, 월별 인덱스가 자동 생성됩니다.

## 폴더 구조
```
manmin-youtube-report/
├── index.html            ← 랜딩(월 목록, 자동 갱신)
├── assets/favicon.svg    ← MANMIN 아이콘
├── build_youtube.py      ← 월간 자동 생성 스크립트
├── 2026-06/
│   ├── index.html        ← 그 달 데이터 인덱스
│   └── data/
│       ├── 개요/         ← Chart data.csv / Table data.csv / Totals.csv
│       ├── 콘텐츠/
│       ├── 트래픽소스/
│       ├── 지역/
│       ├── 연령및성별/
│       ├── 기기/
│       └── 구독상태/
└── README.md
```

## 매월 작업 순서 (약 5분)

### 1. YouTube 스튜디오에서 CSV 내보내기
1. https://studio.youtube.com 접속 → 좌측 **분석** → 우상단 **고급 모드**
2. 기간을 **지난달(전월 1일~말일)** 로 설정
3. 상단 탭을 하나씩 선택하고 우상단 **내보내기 → 쉼표로 구분된 값(.csv)** 클릭
   - 받은 ZIP을 풀면 `Chart data.csv`, `Table data.csv`, `Totals.csv` 가 들어 있음
4. 아래 7개 탭을 각각 내보내 카테고리 폴더에 넣기 (폴더명 그대로 사용):

| 스튜디오 탭 | 넣을 폴더명 | 색인 내용 |
|---|---|---|
| 개요(Overview) | `개요` | 조회수·시청시간·구독자 증감 (KPI) |
| 콘텐츠(Content) | `콘텐츠` | 영상별 조회수 순위 |
| 트래픽 소스 | `트래픽소스` | 유입 경로 분포 |
| 지역(Geography) | `지역` | 시청 국가/지역 분포 |
| 연령 및 성별 | `연령및성별` | 시청자 프로필 |
| 기기 유형 | `기기` | 시청 기기 분포 |
| 시청 지역(구독 상태) | `구독상태` | 구독/비구독 비율 |

> 시간이 없으면 **개요·콘텐츠 2개만** 넣어도 KPI와 영상 순위는 나옵니다. 나머지는 있으면 자동 추가됩니다.

### 2. 인덱스 생성
Claude(Cowork)에게 "이번 달 유튜브 인덱스 만들어줘"라고 요청하거나, 직접 실행:
```
python build_youtube.py --src "CSV상위폴더" --month 2026-07 --period "2026.07 월간"
```
`CSV상위폴더` 안에 위 7개 카테고리 폴더가 있어야 합니다.

### 3. 푸시
**GitHub Desktop** 실행 → 변경사항 확인 → Commit → **Push origin**
→ 1~2분 후 `https://manminkim-eng.github.io/manmin-youtube-report/` 에 반영

## GitHub 최초 설정 (한 번만)
1. GitHub Desktop → File → Add local repository → 이 폴더 선택 → create a repository → 이름 `manmin-youtube-report`
2. Publish repository (**Public** 체크 — Pages는 공개 저장소 필요)
3. github.com → 저장소 → Settings → Pages → Source: `main` / `/(root)` → Save
4. 몇 분 후 `https://manminkim-eng.github.io/manmin-youtube-report/` 공개

## 참고
- 데이터 출처: YouTube 스튜디오 분석(월간). 원본 CSV는 각 달 `data/<카테고리>/` 에 보관됩니다.
- 블로그 리포트와 사이트 구조·톤이 동일하며, 액센트 색만 유튜브 레드(#E23B2E)로 구분했습니다.
- 매월 1일 08:10 갱신 알림 스케줄이 등록되어 있습니다.
