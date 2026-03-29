# 투자 포트폴리오 모니터

Bloomberg 스타일 다크 테마 투자 포트폴리오 모니터링 웹사이트

## 기술 스택

- Frontend: React + Vite + Tailwind CSS (포트 5173)
- Backend: Python FastAPI (포트 8000)
- DB: SQLite

## 실행 방법

### 1. 백엔드 실행

```bash
cd ~/investment-monitor/backend

# 의존성 설치 (최초 1회, pip이 없는 경우)
curl -sS https://bootstrap.pypa.io/get-pip.py | python3 - --user --break-system-packages
~/.local/bin/pip install -r requirements.txt --break-system-packages

# 서버 실행
~/.local/bin/uvicorn main:app --reload
```

백엔드 API 문서: http://localhost:8000/docs

### 2. 프론트엔드 실행

```bash
cd ~/investment-monitor/frontend

# 의존성 설치 (최초 1회)
npm install

# 개발 서버 실행
npm run dev
```

웹사이트: http://localhost:5173

## 주요 기능

### 대시보드
- 총 잔고 / 총 투자금 / 총 평가손익 / 수익률 요약 카드
- 섹터별 비중 도넛 차트 (현금 비중 포함)
- 수익률 현황 바 차트
- 전체 종목 카드 그리드

### 종목 관리
- 종목 클릭 → 현재가, 평균매수가, 목표가, 손절가 수동 업데이트
- 씨앗/에코/피라미딩 단계 뱃지
- 목표가 달성률 프로그레스바
- 현금 대비 추가매수 가능 수량 표시
- 단계별 필터 (씨앗 / 에코 / 피라미딩)
- 종목 추가 기능

### 거래내역
- 최근 거래 타임라인 (읽기전용)

## 초기 데이터

2026.03.27 잔고증명서 기준으로 14개 종목 + 현금 180,277,235원이 로드됩니다.
DB 파일: `backend/investment.db`

DB를 초기화하려면:
```bash
rm ~/investment-monitor/backend/investment.db
# 백엔드 재시작 시 자동으로 재생성
```
