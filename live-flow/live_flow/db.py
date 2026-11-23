"""SQLite 저장 (표준 라이브러리만 사용)."""
from __future__ import annotations

import csv
import io
import sqlite3
from pathlib import Path

from .collector import Snapshot

SCHEMA = """
CREATE TABLE IF NOT EXISTS snapshots (
  ts TEXT NOT NULL,
  market TEXT NOT NULL,
  idx REAL, foreign_eok REAL, inst_eok REAL, indiv_eok REAL, other_corp_eok REAL,
  PRIMARY KEY (ts, market)
);
CREATE INDEX IF NOT EXISTS ix_snap_market_ts ON snapshots(market, ts);
"""
COLS = ["ts", "market", "idx", "foreign_eok", "inst_eok", "indiv_eok", "other_corp_eok"]


class Store:
    def __init__(self, path: str | Path):
        self.path = str(path)
        with self._conn() as c:
            c.executescript(SCHEMA)

    def _conn(self):
        c = sqlite3.connect(self.path, timeout=10)
        c.row_factory = sqlite3.Row
        return c

    def add(self, s: Snapshot) -> None:
        with self._conn() as c:
            c.execute(
                "INSERT OR REPLACE INTO snapshots VALUES (?,?,?,?,?,?,?)",
                (s.ts, s.market, s.index, s.foreign, s.inst, s.indiv, s.other_corp),
            )

    def day(self, market: str, day: str) -> list[dict]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT * FROM snapshots WHERE market=? AND substr(ts,1,10)=? ORDER BY ts",
                (market, day),
            ).fetchall()
        return [dict(r) for r in rows]

    def days(self, market: str, limit: int = 60) -> list[str]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT DISTINCT substr(ts,1,10) d FROM snapshots WHERE market=? ORDER BY d DESC LIMIT ?",
                (market, limit),
            ).fetchall()
        return [r["d"] for r in rows]

    def daily_close(self, market: str, limit: int = 60) -> list[dict]:
        """날짜별 마지막 스냅샷 = 그날 마감 누적."""
        with self._conn() as c:
            rows = c.execute(
                """SELECT s.* FROM snapshots s
                   JOIN (SELECT substr(ts,1,10) d, MAX(ts) mts FROM snapshots WHERE market=? GROUP BY d) m
                     ON s.ts = m.mts AND s.market = ?
                   ORDER BY s.ts DESC LIMIT ?""",
                (market, market, limit),
            ).fetchall()
        return [dict(r) for r in reversed(rows)]

    def csv(self, market: str, day: str) -> str:
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["시각", "지수", "외국인(억)", "기관(억)", "개인(억)", "기타법인(억)"])
        for r in self.day(market, day):
            w.writerow([r["ts"][11:19], r["idx"], r["foreign_eok"], r["inst_eok"], r["indiv_eok"], r["other_corp_eok"]])
        return "﻿" + buf.getvalue()  # 엑셀 한글 깨짐 방지(BOM)
