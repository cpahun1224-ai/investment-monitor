"""GitHub Actions용: 수집 → CSV 누적 → 판정 → 정적 JSON 출력 (서버 불필요).

저장소 안의 파일만 쓴다.
- data/market_reader/daily.csv           : 일별 원자료(종가·투자자별 순매수). 기록이 여기 누적된다.
- frontend/public/market/grade.json      : 최신 판정 요약(시장 판독기 탭이 읽음)
- frontend/public/market/history.json    : 최근 60거래일 판정
"""
from __future__ import annotations

import csv
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

from .grading import DayBar, grade_series, latest_summary
from .rules import RuleConfig
from .sources import DailyRow, Source

KST = ZoneInfo("Asia/Seoul")
REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_CSV = REPO_ROOT / "data" / "market_reader" / "daily.csv"
OUT_DIR = REPO_ROOT / "frontend" / "public" / "market"
FIELDS = ["date", "close", "foreign_net_eok", "inst_net_eok", "indiv_net_eok", "source"]
HISTORY_CALENDAR_DAYS = 130  # 60일선 계산에 필요한 과거 거래일을 넉넉히
CLOSE_CONFIRM = (15, 40)  # 이 시각(KST) 전에는 오늘 값이 장중 가격이라 종가로 쓰지 않는다


def _num(x: str) -> Optional[float]:
    return None if x in ("", None) else float(x)


def load_csv(path: Path = DATA_CSV) -> dict[date, DailyRow]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        return {
            date.fromisoformat(r["date"]): DailyRow(
                date=date.fromisoformat(r["date"]),
                close=float(r["close"]),
                foreign_net_eok=_num(r["foreign_net_eok"]),
                inst_net_eok=_num(r["inst_net_eok"]),
                indiv_net_eok=_num(r["indiv_net_eok"]),
                source=r["source"],
            )
            for r in csv.DictReader(f)
        }


def save_csv(rows: dict[date, DailyRow], path: Path = DATA_CSV) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for d in sorted(rows):
            r = rows[d]
            w.writerow(
                {
                    "date": d.isoformat(),
                    "close": r.close,
                    "foreign_net_eok": "" if r.foreign_net_eok is None else r.foreign_net_eok,
                    "inst_net_eok": "" if r.inst_net_eok is None else r.inst_net_eok,
                    "indiv_net_eok": "" if r.indiv_net_eok is None else r.indiv_net_eok,
                    "source": r.source,
                }
            )


def merge(existing: dict[date, DailyRow], new: list[DailyRow]) -> dict[date, DailyRow]:
    """KRX 값이 우선. KRX에 빈 칸이 있으면 기존(수동 입력) 값을 남긴다."""
    out = dict(existing)
    for r in new:
        old = out.get(r.date)
        if old:
            for f in ("foreign_net_eok", "inst_net_eok", "indiv_net_eok"):
                if getattr(r, f) is None:
                    setattr(r, f, getattr(old, f))
        out[r.date] = r
    return out


def build_outputs(rows: dict[date, DailyRow], cfg: RuleConfig, collector: dict) -> tuple[dict, list]:
    ordered = [rows[d] for d in sorted(rows)]
    judgements = grade_series([DayBar(r.date, r.close, r.foreign_net_eok) for r in ordered], cfg)
    summary = latest_summary(judgements, cfg)
    summary["data_quality"] = {
        "rows": len(ordered),
        "ma60_history_ok": sum(1 for r in ordered if r.date <= cfg.start_date) >= 60,
        "missing_foreign_days": [r.date.isoformat() for r in ordered[-10:] if r.foreign_net_eok is None],
        "manual_days": [r.date.isoformat() for r in ordered[-20:] if r.source == "manual"],
    }
    summary["collector"] = collector
    summary["generated_at"] = datetime.now(KST).isoformat(timespec="seconds")
    history = [j.to_dict() for j in judgements[-60:]]
    return summary, history


def write_outputs(summary: dict, history: list, out_dir: Path = OUT_DIR) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "grade.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    (out_dir / "history.json").write_text(json.dumps(history, ensure_ascii=False, indent=1), encoding="utf-8")


def run(
    source: Optional[Source],
    cfg: Optional[RuleConfig] = None,
    today: Optional[date] = None,
    csv_path: Path = DATA_CSV,
    out_dir: Path = OUT_DIR,
    now: Optional[datetime] = None,
) -> bool:
    """수집 실패해도 저장된 CSV로 판정·출력은 한다. 수집 성공 여부를 돌려준다."""
    cfg = cfg or RuleConfig.from_env()
    now = now or datetime.now(KST)
    today = today or now.date()
    before_close = (now.hour, now.minute) < CLOSE_CONFIRM and now.date() == today
    rows = load_csv(csv_path)
    collector = {"source": getattr(source, "name", "none"), "ok": None, "rows": 0, "error": None}
    if source is not None:
        try:
            new = source.fetch(cfg.start_date - timedelta(days=HISTORY_CALENDAR_DAYS), today)
            if not new:
                raise RuntimeError("KRX가 빈 결과를 돌려줌(휴장·로그인 실패·접속 차단 가능)")
            if before_close:  # 장중 실행: 오늘 행은 종가가 아니므로 버린다(수동 입력은 유지)
                new = [r for r in new if r.date != today]
            rows = merge(rows, new)
            collector.update(ok=True, rows=len(new))
        except Exception as e:  # noqa: BLE001 — 실패 사유를 화면에 그대로 보여 준다
            collector.update(ok=False, error=f"{type(e).__name__}: {e}"[:300])
    if before_close and today in rows and rows[today].source != "manual":
        del rows[today]  # 이전 장중 실행이 남긴 오늘 값 정리
    collector["intraday_skipped"] = before_close
    save_csv(rows, csv_path)
    summary, history = build_outputs(rows, cfg, collector)
    write_outputs(summary, history, out_dir)
    return collector["ok"] is not False


def add_manual(row: DailyRow, csv_path: Path = DATA_CSV) -> None:
    rows = load_csv(csv_path)
    row.source = "manual"
    rows[row.date] = row
    save_csv(rows, csv_path)
