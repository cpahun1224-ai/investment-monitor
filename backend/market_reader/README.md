# 나만의 시장 판독기 (market_reader) — 1단계: 종가 기록기 + 시장 등급 자동 판정

평일 장 마감 후 **GitHub Actions**가 KRX에서 코스피 종가·외국인 현물 순매수를 받아
**05 매수규칙 A절(CIO 승인 2026-11-14)** 대로 RED / ORANGE / YELLOW / GREEN과 이번 달 매수 한도를 판정합니다.
결과는 저장소에 JSON으로 커밋되고, Vercel이 다시 배포해 **'시장 판독기' 탭**에 보입니다. **서버가 필요 없고 무료**입니다.

> 조회 전용 도구입니다. 주문 기능은 없고, 증권 계좌와 연결하지 않습니다. 최종 판단은 CIO가 장 마감 후에 합니다.

## 흐름

```
평일 16:10·18:10 KST  GitHub Actions(.github/workflows/market-reader.yml)
   └ python -m market_reader export
        ├ KRX(pykrx) 수집 → data/market_reader/daily.csv 에 누적
        ├ 05-A 판정
        └ frontend/public/market/grade.json, history.json 작성 → 커밋 → Vercel 재배포
```

수집에 실패해도 저장된 CSV로 판정은 갱신하고, 화면에 빨간 경고를 띄우며, Actions 실행이 실패로 표시됩니다(GitHub 알림 메일).

## 처음 설정 (한 번)

1. GitHub 저장소 → **Settings → Secrets and variables → Actions → New repository secret**
   - `KRX_ID` : data.krx.co.kr 아이디
   - `KRX_PW` : data.krx.co.kr 비밀번호 (카카오 로그인 계정은 '비밀번호 찾기'로 비밀번호를 먼저 만든다)
2. **Actions → market-reader → Run workflow** (mode: export)로 첫 실행 → 성공하면 이후 자동

## 수동 입력 (KRX 수집이 막힌 날)

Actions → market-reader → Run workflow → mode: `manual`, 날짜·종가·외국인 순매수(억원) 입력.
나중에 KRX 값이 들어오면 KRX 값이 우선하고, KRX에 빈 칸이 있으면 수동 값을 남깁니다.

명령줄(backend 폴더): `python -m market_reader export` / `export --no-collect` / `manual 2026-11-23 4700.12 -411`

## 판정 내용

| 판정 | 규칙(05-A) |
|---|---|
| RED → ORANGE | ① 종가 20일선 위 ② 다음 날 유지 ③ 기준 저점 위 저점 상승 ④ 2거래일 외국인 순매수 합계 + |
| ORANGE → YELLOW | ① 20일선 3거래일 연속 상승 ② 6,000 종가 돌파 |
| YELLOW → GREEN | ① 60일선 종가 회복 ② 다음 날 유지 |
| 하향 | 상위 등급에서 20일선 이탈 후 2거래일 내 회복 실패 → 한 단계 하향 / 구조적 RED → 즉시 RED |
| RED 상태 이벤트 | 기준 저점(4,911.28) 종가 이탈 + 다음 날 회복 실패 → **현금 복구 2단계 상정** |
| 월 매수 한도 | RED 0% / ORANGE 2% / YELLOW 5% / GREEN 10% |

데이터가 없는 조건은 ❔(미확인)이며 **통과로 세지 않습니다**.

## 규칙 수치 바꾸기 (CIO 승인 후)

`rules.py`의 기본값 또는 워크플로 `env`에 `MR_REFERENCE_LOW`, `MR_YELLOW_BREAKOUT`, `MR_START_DATE`, `MR_START_GRADE`.

## 해석 목록 (CIO 확인 필요)

1. **'저점 높이기'(ORANGE 조건 ③)** = 확인 2일 종가가 기준 저점 위 + 최근 10거래일 최저 종가 > 그 이전 20거래일 최저 종가.
2. **기준 저점이 깨진 뒤**에는 엔진이 기준을 스스로 바꾸지 않고 "기준 저점 갱신 검토"를 CIO 안건으로 띄웁니다. 갱신 전까지 ORANGE 조건 ③은 충족되지 않습니다.
3. **구조적 RED ③(고점·저점 동반 하락)** = 최근 20거래일 최고·최저 종가가 그 이전 20거래일보다 모두 낮음.
4. **외국인 순매수** = KRX 유가증권시장 투자자별 거래실적의 '외국인합계'(pykrx 기본값, ETF 제외). 언론 보도와 약간 다를 수 있습니다.
5. **하향 2거래일** = 이탈일 포함 3일 연속 20일선 아래면 그날 하향.

## 알려진 제약

- GitHub 예약 실행은 수 분~수십 분 늦게 시작될 수 있습니다(18:10 재실행으로 보완).
- GitHub 실행 서버는 해외에 있습니다. KRX가 해외 접속을 막으면 첫 실행에서 실패로 드러나며, 그때 수동 입력 또는 다른 실행 위치로 바꿉니다.

## 2단계 예정

KIS Open API로 장중 30초 수급 수집(사내 대시보드 수준), 종가 판정 후 카카오톡 알림.
