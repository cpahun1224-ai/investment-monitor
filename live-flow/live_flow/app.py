"""30초 수급 대시보드 서버.

실행(live-flow 폴더에서):  python -m uvicorn live_flow.app:app --host 0.0.0.0 --port 8501
설정: live-flow/.env  (KRX_ID, KRX_PW, LIVE_FLOW_PASSWORD)
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
store = Store(os.getenv("LIVE_FLOW_DB", str(ROOT / "live_flow.db")))
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
