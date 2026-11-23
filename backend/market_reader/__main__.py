"""명령줄 실행 (backend 폴더에서). GitHub Actions도 이 명령을 쓴다.

    python -m market_reader export               # KRX 수집 + 판정 + JSON 출력
    python -m market_reader export --no-collect  # 저장된 CSV로 판정만
    python -m market_reader manual 2026-11-23 4700.12 -411   # 날짜 종가 [외국인순매수(억원)] 입력 후 판정
"""
from __future__ import annotations

import json
import sys
from datetime import date

from .export import OUT_DIR, add_manual, run
from .sources import DailyRow, PykrxSource


def main(argv: list[str]) -> int:
    cmd = argv[1] if len(argv) > 1 else "export"
    if cmd == "export":
        ok = run(None if "--no-collect" in argv else PykrxSource())
    elif cmd == "manual" and len(argv) >= 4:
        d, close = date.fromisoformat(argv[2]), float(argv[3])
        fnet = float(argv[4]) if len(argv) > 4 and argv[4] != "" else None
        add_manual(DailyRow(d, close, fnet))
        ok = run(None)
    else:
        print(__doc__)
        return 2
    s = json.loads((OUT_DIR / "grade.json").read_text(encoding="utf-8"))
    latest = s.get("latest", {})
    print(f"as_of={s.get('as_of')} grade={latest.get('grade')} events={latest.get('events')}")
    print(f"collector={s.get('collector')}")
    for a in s.get("cio_agenda", []):
        print(f"CIO 안건: {a}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
