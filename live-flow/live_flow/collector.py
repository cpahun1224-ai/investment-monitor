"""KRX 장중 스냅샷 수집 (30초 간격).

KRX 정보데이터시스템은 장중에 '오늘' 행을 돌려준다.
- 지수: get_index_ohlcv(오늘, 오늘, 코드)의 '종가' = 현재 지수
- 투자자별: get_market_trading_value_by_date(오늘, 오늘, 시장)의 순매수 = 장 시작부터 누적
(2026-11-23 13:38 실측: 외국인 −2,663.5억 ↔ 사내 대시보드 13:40 −2,666억)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")
EOK = 100_000_000
MARKETS = {"KOSPI": "1001", "KOSDAQ": "2001"}  # 시장명 → 지수 코드
log = logging.getLogger("live_flow")


@dataclass
class Snapshot:
    ts: str  # KST ISO 초 단위
    market: str
    index: Optional[float]
    foreign: Optional[float]  # 억원, 누적 순매수
    inst: Optional[float]
    indiv: Optional[float]
    other_corp: Optional[float]

    def as_row(self) -> dict:
        return asdict(self)


def _eok(df, col) -> Optional[float]:
    if df is None or df.empty or col not in df.columns:
        return None
    return round(float(df.iloc[-1][col]) / EOK, 1)


def fetch_snapshot(market: str, now: Optional[datetime] = None) -> Snapshot:
    from pykrx import stock

    now = now or datetime.now(KST)
    d = now.strftime("%Y%m%d")
    idx = stock.get_index_ohlcv(d, d, MARKETS[market])
    flows = stock.get_market_trading_value_by_date(d, d, market)
    index = None if idx is None or idx.empty else float(idx.iloc[-1]["종가"])
    return Snapshot(
        ts=now.isoformat(timespec="seconds"),
        market=market,
        index=index,
        foreign=_eok(flows, "외국인합계"),
        inst=_eok(flows, "기관합계"),
        indiv=_eok(flows, "개인"),
        other_corp=_eok(flows, "기타법인"),
    )


def is_collect_time(now: datetime) -> bool:
    """평일 09:00~15:35 KST (15:30 종가 반영분까지)."""
    if now.weekday() >= 5:
        return False
    hm = (now.hour, now.minute)
    return (9, 0) <= hm <= (15, 35)
