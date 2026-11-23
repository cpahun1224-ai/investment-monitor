"""명령줄 실행 (Railway cron 또는 수동 점검용).

    python -m market_reader run       # 수집 + 판정 + 요약 출력
    python -m market_reader grade     # 저장된 데이터로 판정만
    python -m market_reader manual 2026-11-23 4700.12 -411   # 날짜 종가 외국인순매수(억원)
"""
from __future__ import annotations

import json
import sys
from datetime import date

from .rules import RuleConfig
from .service import add_manual, collect, regrade
from .sources import DailyRow, PykrxSource
from .store import get_engine


def main(argv: list[str]) -> int:
    cmd = argv[1] if len(argv) > 1 else "run"
    cfg = RuleConfig.from_env()
    eng = get_engine()
    if cmd == "run":
        print(f"collected {collect(eng, PykrxSource(), cfg)} rows")
    elif cmd == "manual":
        d, close = date.fromisoformat(argv[2]), float(argv[3])
        fnet = float(argv[4]) if len(argv) > 4 else None
        add_manual(eng, DailyRow(d, close, fnet))
    elif cmd != "grade":
        print(__doc__)
        return 2
    print(json.dumps(regrade(eng, cfg), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
