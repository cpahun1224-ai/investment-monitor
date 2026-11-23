# 나만의 시장 판독기 (market_reader) — 1단계: 종가 기록기 + 시장 등급 자동 판정

`investment-monitor`(FastAPI + React/Vite)에 끼워 넣는 모듈입니다.
매 거래일 장 마감 후 코스피 종가·외국인 현물 순매수를 저장하고, **05 매수규칙 A절(CIO 승인 2026-11-14)** 대로
RED / ORANGE / YELLOW / GREEN 등급과 이번 달 매수 한도를 자동 판정합니다.

> 조회 전용 도구입니다. 주문 기능은 없고, 증권 계좌와 연결하지 않습니다. 최종 판단은 CIO가 장 마감 후에 합니다.

## 무엇을 판정하나

| 판정 | 규칙(05-A) | 화면 표시 |
|---|---|---|
| RED → ORANGE | ① 종가 20일선 위 ② 다음 날 유지 ③ 기준 저점 위 저점 상승 ④ 2거래일 외국인 순매수 합계 + | 조건별 ✅/❌/❔ |
| ORANGE → YELLOW | ① 20일선 3거래일 연속 상승 ② 6,000 종가 돌파 | 〃 |
| YELLOW → GREEN | ① 60일선 종가 회복 ② 다음 날 유지 | 〃 |
| 하향 | 상위 등급에서 20일선 이탈 후 2거래일 내 회복 실패 → 한 단계 하향 / 구조적 RED → 즉시 RED | 하향 감시 |
| RED 상태 이벤트 | 기준 저점(4,911.28) 종가 이탈 + 다음 날 회복 실패 → **현금 복구 2단계 상정** | CIO 안건 |
| 월 매수 한도 | RED 0% / ORANGE 2% / YELLOW 5% / GREEN 10% | 상단 우측 |

데이터가 없는 조건은 ❔(미확인)이며 **통과로 세지 않습니다**.

## 폴더 (backend/ 기준)

```
market_reader/
  rules.py     규칙 상수(기준 저점·6,000·시작 등급) — 환경변수로 덮어쓰기
  grading.py   판정 엔진(순수 함수)
  sources.py   데이터 출처(pykrx). 2단계에서 KIS Open API 추가 예정
  store.py     SQLite / Postgres 저장
  service.py   수집 → 저장 → 재판정
  api.py       FastAPI 라우터 + 16:10·18:10 KST 자동 실행
  __main__.py  명령줄 실행
tests/test_*.py                pytest 11개 (backend 폴더에서 `python -m pytest tests`)
../frontend/src/components/MarketGradePanel.jsx  '시장 판독기' 탭
```

## 앱 연결 상태

- `main.py`: `app.include_router(market_router)`, startup에서 `maybe_start_scheduler()` 호출
- 저장: 기본은 기존 앱과 같은 SQLite 파일(`DATABASE_PATH`). `DATABASE_URL`(Postgres)이 있으면 그쪽 사용
- 첫 배포 직후 DB가 비어 있으면 서버 시작 시 한 번 바로 수집
- 프론트: 상단 탭 '시장 판독기'

## 환경변수 (Railway)

| 이름 | 필수 | 설명 |
|---|---|---|
| `KRX_ID`, `KRX_PW` | ✅ | KRX 정보데이터시스템(data.krx.co.kr) 회원 계정. 최신 pykrx는 로그인이 필요합니다 |
| `DATABASE_URL` | | 있으면 Postgres 사용. 없으면 `DATABASE_PATH` SQLite(볼륨이 없으면 재배포 때 지워짐) |
| `MARKET_READER_TOKEN` | ✅ | 수집·수동 입력 API 보호용 임의 문자열 |
| `MR_REFERENCE_LOW` | | 기준 저점. 기본 4911.28. **CIO 승인 후에만** 바꿈 |
| `MR_START_DATE`, `MR_START_GRADE` | | 판정 시작일·등급. 기본 2026-11-14, RED |
| `MARKET_READER_SCHEDULER` | | `0`이면 앱 내부 자동 실행 끔(Railway cron 쓸 때) |

## API

| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | `/api/market/grade` | 최신 등급·조건표·CIO 안건 |
| GET | `/api/market/history?limit=60` | 날짜별 판정 기록 |
| POST | `/api/market/collect` | 지금 수집 + 재판정 (헤더 `X-Admin-Token`) |
| POST | `/api/market/manual` | 수집 실패일 수동 입력 `{date, close, foreign_net_eok}` (헤더 `X-Admin-Token`) |

명령줄: `python -m market_reader run` / `grade` / `manual 2026-11-23 4700.12 -411`

## 해석 목록 (CIO 확인 필요)

규칙 문장을 코드로 옮기면서 해석한 부분입니다. 다르게 보시면 숫자 하나만 바꾸면 됩니다.

1. **'저점 높이기'(ORANGE 조건 ③)** = 확인 2일 종가가 기준 저점 위 + 최근 10거래일 최저 종가 > 그 이전 20거래일 최저 종가.
2. **기준 저점이 깨진 뒤**에는 엔진이 기준을 스스로 바꾸지 않고 "기준 저점 갱신 검토"를 CIO 안건으로 띄웁니다. 갱신 전까지 ORANGE 조건 ③은 충족되지 않습니다.
3. **구조적 RED ③(고점·저점 동반 하락)** = 최근 20거래일 최고·최저 종가가 그 이전 20거래일보다 모두 낮음.
4. **외국인 순매수** = KRX 유가증권시장 투자자별 거래실적의 '외국인합계'(pykrx 기본값, ETF 제외). 언론 보도 수치와 약간 다를 수 있습니다.
5. **하향 2거래일** = 이탈일 포함 3일 연속 20일선 아래면 그날 하향.

## 2단계 예정

KIS Open API로 장중 30초 수급 수집(사내 대시보드 수준), 종가 판정 후 카카오톡 알림.
