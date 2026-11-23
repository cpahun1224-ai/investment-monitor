"""FastAPI 연결부.

main.py에서 include_router(market_router)로 붙이고, startup 이벤트에서 maybe_start_scheduler()를 부른다.
MARKET_READER_SCHEDULER=0 이면 앱 내부 자동 실행을 끈다(Railway cron에서 `python -m market_reader run` 사용 시).
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import date, datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from .rules import RuleConfig
from .service import add_manual, collect, regrade
from .sources import DailyRow, PykrxSource
from .store import get_engine, load_grades

log = logging.getLogger("market_reader")
KST = ZoneInfo("Asia/Seoul")
RUN_TIMES = [(16, 10), (18, 10)]  # 잠정치 → 확정치 덮어쓰기

router = APIRouter(prefix="/api/market", tags=["market-reader"])
_engine = None


def engine():
    global _engine
    if _engine is None:
        _engine = get_engine()
    return _engine


def require_admin(x_admin_token: Optional[str] = Header(default=None)):
    token = os.getenv("MARKET_READER_TOKEN")
    if not token:
        raise HTTPException(503, "MARKET_READER_TOKEN이 설정되지 않아 쓰기 API를 막아 두었습니다")
    if x_admin_token != token:
        raise HTTPException(401, "토큰이 맞지 않습니다")


@router.get("/grade")
def get_grade():
    """최신 등급·조건 점검표·CIO 안건. 화면은 이것 하나만 부르면 된다."""
    return regrade(engine(), RuleConfig.from_env())


@router.get("/history")
def get_history(limit: int = 60):
    return load_grades(engine(), limit=min(limit, 250))


@router.post("/collect", dependencies=[Depends(require_admin)])
def post_collect():
    cfg = RuleConfig.from_env()
    n = collect(engine(), PykrxSource(), cfg)
    return {"collected": n, "summary": regrade(engine(), cfg)}


class ManualDay(BaseModel):
    date: date
    close: float = Field(gt=0, description="코스피 종가")
    foreign_net_eok: Optional[float] = Field(None, description="유가증권시장 외국인 현물 순매수(억원)")
    inst_net_eok: Optional[float] = None
    indiv_net_eok: Optional[float] = None


@router.post("/manual", dependencies=[Depends(require_admin)])
def post_manual(day: ManualDay):
    add_manual(engine(), DailyRow(**day.model_dump()))
    return regrade(engine(), RuleConfig.from_env())


# ── 스케줄러 ────────────────────────────────────────────────


def _next_run(now: datetime) -> datetime:
    for add in range(0, 8):
        d = (now + timedelta(days=add)).date()
        if d.weekday() >= 5:
            continue
        for h, m in RUN_TIMES:
            t = datetime(d.year, d.month, d.day, h, m, tzinfo=KST)
            if t > now:
                return t
    raise RuntimeError("next run not found")


async def _bootstrap_if_empty():
    """첫 배포 직후 DB가 비어 있으면 한 번 바로 채운다(16:10을 기다리지 않도록)."""
    from .store import load_daily

    if await asyncio.to_thread(load_daily, engine()):
        return
    try:
        cfg = RuleConfig.from_env()
        await asyncio.to_thread(collect, engine(), PykrxSource(), cfg)
        await asyncio.to_thread(regrade, engine(), cfg)
        log.info("market_reader 초기 수집 완료")
    except Exception:
        log.exception("market_reader 초기 수집 실패(KRX_ID/KRX_PW 확인)")


async def _loop():
    await _bootstrap_if_empty()
    while True:
        now = datetime.now(KST)
        nxt = _next_run(now)
        await asyncio.sleep((nxt - now).total_seconds())
        try:
            cfg = RuleConfig.from_env()
            n = await asyncio.to_thread(collect, engine(), PykrxSource(), cfg)
            summary = await asyncio.to_thread(regrade, engine(), cfg)
            log.info("market_reader collected=%s grade=%s", n, summary.get("latest", {}).get("grade"))
        except Exception:  # 휴장·KRX 장애여도 루프는 계속
            log.exception("market_reader 수집 실패")


def start_scheduler() -> asyncio.Task:
    return asyncio.create_task(_loop())


def maybe_start_scheduler():
    if os.getenv("MARKET_READER_SCHEDULER", "1") == "1":
        return start_scheduler()
    return None
