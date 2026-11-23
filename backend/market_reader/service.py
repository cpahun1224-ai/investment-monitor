"""수집 → 저장 → 전체 재판정. 등급은 상태 기계라서 매번 시작일부터 다시 계산한다(수십 행이라 부담 없음)."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from sqlalchemy.engine import Engine

from .grading import DayBar, grade_series, latest_summary
from .rules import RuleConfig
from .sources import DailyRow, Source
from .store import load_daily, save_grades, upsert_daily

# 60일선 계산에 필요한 과거 거래일을 넉넉히(달력 기준 약 4개월)
HISTORY_CALENDAR_DAYS = 130


def collect(engine: Engine, source: Source, cfg: RuleConfig, today: Optional[date] = None) -> int:
    today = today or date.today()
    start = cfg.start_date - timedelta(days=HISTORY_CALENDAR_DAYS)
    rows = source.fetch(start, today)
    return upsert_daily(engine, rows)


def regrade(engine: Engine, cfg: RuleConfig) -> dict:
    rows = load_daily(engine)
    bars = [DayBar(r.date, r.close, r.foreign_net_eok) for r in rows]
    judgements = grade_series(bars, cfg)
    save_grades(engine, judgements, cfg.reference_low)
    summary = latest_summary(judgements, cfg)
    ma_ready = sum(1 for r in rows if r.date <= cfg.start_date) >= 60
    summary["data_quality"] = {
        "rows": len(rows),
        "ma60_history_ok": ma_ready,
        "missing_foreign_days": [r.date.isoformat() for r in rows[-10:] if r.foreign_net_eok is None],
    }
    return summary


def add_manual(engine: Engine, row: DailyRow) -> None:
    """수집기가 실패한 날 지헌님이 토스·사내 대시보드 수치로 직접 넣는 경로."""
    row.source = "manual"
    upsert_daily(engine, [row])
