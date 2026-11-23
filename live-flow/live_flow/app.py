"""30초 수급 대시보드 서버.

실행(live-flow 폴더에서):  python -m uvicorn live_flow.app:app --host 0.0.0.0 --port 8501
설정: 환경변수 또는 live-flow/.env  (KRX_ID, KRX_PW, LIVE_FLOW_PASSWORD, DATABASE_URL)
Render 무료 서버는 15분간 요청이 없으면 잠들므로, 외부 깨우기 서비스가 장중에 /healthz 를 호출한다.
"""
from __future__ import annotations

import asyncio
import logging
import os
import secrets
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles

from .collector import KST, MARKETS, fetch_snapshot, is_collect_time
from .db import Store
from .committee import summarize

ROOT = Path(__file__).resolve().parent.parent
INTERVAL = int(os.getenv("LIVE_FLOW_INTERVAL", "30"))
log = logging.getLogger("live_flow")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def load_env(path: Path = ROOT / ".env") -> None:
    """python-dotenv 없이 KEY=VALUE 읽기. 이미 있는 환경변수는 덮어쓰지 않는다."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


load_env()
# 운영(Render): DATABASE_URL = Neon Postgres 주소. 로컬: live_flow.db 파일
store = Store(os.getenv("DATABASE_URL") or os.getenv("LIVE_FLOW_DB") or str(ROOT / "live_flow.db"))
status = {"last_ok": None, "last_error": None, "last_error_at": None, "collecting": False}


def collect_once(now: Optional[datetime] = None) -> int:
    now = now or datetime.now(KST)
    n = 0
    for m in MARKETS:
        try:
            s = fetch_snapshot(m, now)
            if s.index is None and s.foreign is None:
                raise RuntimeError("KRX 빈 응답(로그인 또는 장 시작 전)")
            store.add(s)
            n += 1
        except Exception as e:  # noqa: BLE001
            status.update(last_error=f"{m}: {type(e).__name__}: {e}"[:300], last_error_at=now.isoformat(timespec="seconds"))
            log.warning("수집 실패 %s: %s", m, e)
    if n:
        status["last_ok"] = now.isoformat(timespec="seconds")
    return n


async def loop():
    while True:
        now = datetime.now(KST)
        status["collecting"] = is_collect_time(now)
        if status["collecting"]:
            await asyncio.to_thread(collect_once, now)
        # 다음 :00 또는 :30초에 맞춘다
        await asyncio.sleep(INTERVAL - (datetime.now(KST).second % INTERVAL) + 0.5)


@asynccontextmanager
async def lifespan(app):
    task = asyncio.create_task(loop())
    yield
    task.cancel()


app = FastAPI(title="live-flow", lifespan=lifespan, docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")
security = HTTPBasic(auto_error=False)


def auth(cred: Optional[HTTPBasicCredentials] = Depends(security)):
    pw = os.getenv("LIVE_FLOW_PASSWORD")
    if not pw:
        return  # 비밀번호 미설정: Tailscale 등 사설망 안에서만 쓸 때
    ok = cred is not None and secrets.compare_digest(cred.password.encode(), pw.encode())
    if not ok:
        raise HTTPException(401, "비밀번호가 필요합니다", headers={"WWW-Authenticate": "Basic"})


def _market(m: str) -> str:
    m = m.upper()
    if m not in MARKETS:
        raise HTTPException(400, "market은 KOSPI 또는 KOSDAQ")
    return m


@app.get("/healthz")
def healthz():
    """깨우기(cron-job.org)·상태 확인용. 비밀번호 없이 최소 정보만."""
    return {"ok": True, "collecting": status["collecting"], "last_ok": status["last_ok"]}


_prev_cache: dict = {}


def prev_close(market: str, day: str) -> Optional[dict]:
    """전 거래일 마감값. 우리 DB에 있으면 그것, 없으면 KRX 일별 자료로 한 번 받아 둔다."""
    mine = [r for r in store.daily_close(market, 30) if r["ts"][:10] < day]
    if mine and mine[-1]["ts"][11:16] >= "15:30":
        return mine[-1]
    key = (market, day)
    if key in _prev_cache:
        return _prev_cache[key]
    try:
        from datetime import date, timedelta

        from pykrx import stock

        d = date.fromisoformat(day)
        s, e = (d - timedelta(days=14)).strftime("%Y%m%d"), (d - timedelta(days=1)).strftime("%Y%m%d")
        idx = stock.get_index_ohlcv(s, e, MARKETS[market])
        fl = stock.get_market_trading_value_by_date(s, e, market)
        if idx.empty:
            return None
        ts = idx.index[-1]
        row = {"ts": ts.strftime("%Y-%m-%d") + "T15:30:00+09:00", "idx": float(idx.iloc[-1]["종가"]), "foreign_eok": None}
        if ts in fl.index:
            row["foreign_eok"] = round(float(fl.loc[ts]["외국인합계"]) / 1e8, 1)
        _prev_cache[key] = row
        return row
    except Exception as e:  # noqa: BLE001
        log.warning("전일 값 조회 실패: %s", e)
        return None


@app.get("/api/committee")
def api_committee(date: Optional[str] = None):
    """투자위원회용 요약(공개). KRX 공개 시장 데이터만 담고 계좌 정보는 없다."""
    d = date or datetime.now(KST).date().isoformat()
    return {
        "date": d,
        "generated_at": datetime.now(KST).isoformat(timespec="seconds"),
        "collector": {"collecting": status["collecting"], "last_ok": status["last_ok"],
                      "last_error": status["last_error"], "last_error_at": status["last_error_at"]},
        "markets": {m: _market_summary(m, d) for m in MARKETS},
    }


def _market_summary(m: str, d: str) -> dict:
    rows = store.day(m, d)
    return summarize(rows, prev_close(m, d) if rows else None, m)


@app.get("/", dependencies=[Depends(auth)])
def index():
    return FileResponse(Path(__file__).parent / "static" / "index.html")


@app.get("/api/day", dependencies=[Depends(auth)])
def api_day(market: str = "KOSPI", date: Optional[str] = None):
    m = _market(market)
    d = date or datetime.now(KST).date().isoformat()
    return {"market": m, "date": d, "rows": store.day(m, d), "status": status}


@app.get("/api/days", dependencies=[Depends(auth)])
def api_days(market: str = "KOSPI"):
    return store.days(_market(market))


@app.get("/api/daily", dependencies=[Depends(auth)])
def api_daily(market: str = "KOSPI", limit: int = Query(60, le=250)):
    return store.daily_close(_market(market), limit)


@app.get("/api/csv", dependencies=[Depends(auth)])
def api_csv(market: str = "KOSPI", date: Optional[str] = None):
    m = _market(market)
    d = date or datetime.now(KST).date().isoformat()
    return PlainTextResponse(
        store.csv(m, d),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="flow_{m}_{d}.csv"'},
    )


@app.post("/api/collect-now", dependencies=[Depends(auth)])
def api_collect_now():
    """장 시간 외에도 지금 값을 한 번 받아 본다(연결 점검용)."""
    return {"stored": collect_once(), "status": status}
