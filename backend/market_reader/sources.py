"""일봉 데이터 출처.

- PykrxSource: KRX 정보데이터시스템(pykrx). 최근 pykrx는 KRX 로그인이 필요해 KRX_ID/KRX_PW 환경변수를 쓴다.
- 장 마감 직후 외국인 순매수는 잠정치일 수 있어 18:10에 한 번 더 받아 덮어쓴다(scheduler 참조).
- 출처를 바꾸려면 fetch(start, end) -> list[DailyRow]만 구현하면 된다(예: 2단계 KIS Open API).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional, Protocol

KOSPI_INDEX_CODE = "1001"
EOK = 100_000_000  # 1억원


@dataclass
class DailyRow:
    date: date
    close: float
    foreign_net_eok: Optional[float]
    inst_net_eok: Optional[float] = None
    indiv_net_eok: Optional[float] = None
    source: str = "unknown"


class Source(Protocol):
    name: str

    def fetch(self, start: date, end: date) -> list[DailyRow]: ...


class PykrxSource:
    name = "pykrx"

    def fetch(self, start: date, end: date) -> list[DailyRow]:
        from pykrx import stock  # 무거운 import는 실제 호출 때만

        s, e = start.strftime("%Y%m%d"), end.strftime("%Y%m%d")
        idx = stock.get_index_ohlcv(s, e, KOSPI_INDEX_CODE)
        flows = stock.get_market_trading_value_by_date(s, e, "KOSPI")

        rows: list[DailyRow] = []
        for ts, r in idx.iterrows():
            d = ts.date()
            f = flows.loc[ts] if ts in flows.index else None

            def eok(col: str) -> Optional[float]:
                if f is None or col not in f:
                    return None
                return round(float(f[col]) / EOK, 1)

            rows.append(
                DailyRow(
                    date=d,
                    close=float(r["종가"]),
                    foreign_net_eok=eok("외국인합계"),
                    inst_net_eok=eok("기관합계"),
                    indiv_net_eok=eok("개인"),
                    source=self.name,
                )
            )
        return rows
