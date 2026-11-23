# 30초 수급 대시보드 (live-flow) — 2단계

장중(평일 09:00~15:35) **30초마다** KRX에서 코스피·코스닥 지수와 **외국인·기관·개인 현물 누적 순매수**를 받아
사내 대시보드처럼 선 그래프로 보여 줍니다. 집 PC에서 돌리고, 휴대폰에서는 **Tailscale**로 접속합니다.

> 조회 전용입니다. 주문 기능·계좌 연결이 없습니다. 장중 화면은 시나리오 작성용이고, 판단은 15:30 종가 확정 후에 합니다(05 문서 E절).

## 처음 설치 (집 PC, 한 번)

1. GitHub 저장소 → 초록 **Code → Download ZIP** → 압축을 `C:\Users\<이름>\live-flow-app` 같은 곳에 풉니다.
   그 안의 `live-flow` 폴더를 씁니다.
2. `live-flow\setup.bat` 더블클릭 → 설치가 끝나면 메모장이 열립니다.
   `KRX_PW`(KRX 비밀번호)와 `LIVE_FLOW_PASSWORD`(대시보드 비밀번호)를 채우고 저장합니다.
3. `start.bat` 더블클릭 → 브라우저에서 **http://localhost:8501** 접속.
   - 처음 실행할 때 Windows 방화벽 창이 뜨면 **개인 네트워크 허용**을 누릅니다.
   - 검은 창을 닫으면 수집이 멈춥니다(최소화해 두세요).
4. (선택) `install_autostart.bat` 더블클릭 → Windows 로그인할 때마다 자동으로 켜집니다.
5. **절전 끄기**: 설정 → 시스템 → 전원 → 화면/절전 → '절전 모드: 안 함'(전원 연결 시). PC가 잠들면 수집이 멈춥니다.

## 휴대폰에서 보기 (Tailscale, 무료)

1. PC와 휴대폰에 **Tailscale** 앱을 설치하고 **같은 계정**으로 로그인합니다(tailscale.com).
2. 휴대폰 브라우저에서 **http://pc:8501** (PC 이름이 `pc`가 아니면 Tailscale 앱에 보이는 PC 이름).
3. 비밀번호 창이 뜨면 아이디는 아무거나, 비밀번호는 `.env`의 `LIVE_FLOW_PASSWORD`.

Tailscale은 지헌님 기기끼리만 연결되는 사설망이라 인터넷에 공개되지 않습니다.

## 화면

- 코스피/코스닥 탭, 날짜 선택(과거일 조회), 30초 자동 갱신
- 지수(왼쪽 축)와 외국인·기관·개인 누적 순매수(오른쪽 축, 억원), 전일 종가 점선
- 30초 변화량 표, **엑셀(CSV) 다운로드**
- 수집 오류가 나면 빨간 안내가 뜹니다(KRX 로그인 실패·인터넷 끊김 등)

## 데이터와 한계

- 출처: KRX 정보데이터시스템(pykrx). 2026-11-23 13:38 실측에서 외국인 −2,663.5억 ↔ 사내 대시보드 13:40 −2,666억으로 일치.
- KRX의 장중 갱신 주기가 30초보다 길면 같은 값이 몇 줄 이어질 수 있습니다.
- **외국인·기관 선물, 프로그램 차익·비차익은 아직 없습니다.** KRX에서 받을 수 있는지 확인 후 추가하거나, 한국투자증권 API로 넣습니다.
- 요청량: 30초마다 4건(지수 2 + 수급 2). KRX가 막으면 수집 간격을 늘리거나(`.env`에 `LIVE_FLOW_INTERVAL=60`) 다른 출처로 바꿉니다.

## 파일

```
live-flow/
  setup.bat / start.bat / install_autostart.bat   Windows 실행 파일
  .env.example        설정 견본 (.env는 GitHub에 올라가지 않음)
  live_flow/collector.py   KRX 30초 스냅샷
  live_flow/db.py          SQLite(live_flow.db), CSV
  live_flow/app.py         FastAPI 서버 + 수집 루프 + 비밀번호
  live_flow/static/        대시보드 화면, Chart.js(MIT)
  tests/                   pytest
```

API: `/api/day?market=KOSPI&date=YYYY-MM-DD`, `/api/days`, `/api/daily`, `/api/csv`, `POST /api/collect-now`(연결 점검)
