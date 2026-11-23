"""저장소. DATABASE_URL이 있으면 Postgres(Neon 등), 없으면 로컬 SQLite 파일.

SQLAlchemy Core + 표준 SQL만 써서 두 DB에서 같은 코드로 동작한다.
"""
from __future__ import annotations

import csv
import io
from pathlib import Path

from sqlalchemy import create_engine, text

from .collector import Snapshot

SCHEMA = [
    """CREATE TABLE IF NOT EXISTS snapshots (
         ts TEXT NOT NULL,
         market TEXT NOT NULL,
         idx DOUBLE PRECISION, foreign_eok DOUBLE PRECISION, inst_eok DOUBLE PRECISION,
         indiv_eok DOUBLE PRECISION, other_corp_eok DOUBLE PRECISION,
         PRIMARY KEY (ts, market))""",
    "CREATE INDEX IF NOT EXISTS ix_snap_market_ts ON snapshots(market, ts)",
]
UPSERT = text(
    """INSERT INTO snapshots (ts, market, idx, foreign_eok, inst_eok, indiv_eok, other_corp_eok)
       VALUES (:ts, :market, :idx, :foreign_eok, :inst_eok, :indiv_eok, :other_corp_eok)
       ON CONFLICT (ts, market) DO UPDATE SET
         idx = excluded.idx, foreign_eok = excluded.foreign_eok, inst_eok = excluded.inst_eok,
         indiv_eok = excluded.indiv_eok, other_corp_eok = excluded.other_corp_eok"""
)


def normalize_url(url: str) -> str:
    """Neon/Render의 postgres:// 주소를 psycopg(3) 드라이버 주소로."""
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


class Store:
    def __init__(self, url_or_path: str | Path):
        s = str(url_or_path)
        url = normalize_url(s) if "://" in s else f"sqlite:///{s}"
        self.engine = create_engine(url, pool_pre_ping=True, pool_recycle=300, future=True)
        with self.engine.begin() as c:
            for stmt in SCHEMA:
                c.execute(text(stmt))

    def add(self, s: Snapshot) -> None:
        with self.engine.begin() as c:
            c.execute(
                UPSERT,
                dict(ts=s.ts, market=s.market, idx=s.index, foreign_eok=s.foreign,
                     inst_eok=s.inst, indiv_eok=s.indiv, other_corp_eok=s.other_corp),
            )

    def _rows(self, sql: str, **params) -> list[dict]:
        with self.engine.connect() as c:
            return [dict(r._mapping) for r in c.execute(text(sql), params)]

    def day(self, market: str, day: str) -> list[dict]:
        return self._rows(
            "SELECT * FROM snapshots WHERE market=:m AND substr(ts,1,10)=:d ORDER BY ts", m=market, d=day
        )

    def days(self, market: str, limit: int = 60) -> list[str]:
        rows = self._rows(
            "SELECT DISTINCT substr(ts,1,10) AS d FROM snapshots WHERE market=:m ORDER BY d DESC LIMIT :n",
            m=market, n=limit,
        )
        return [r["d"] for r in rows]

    def daily_close(self, market: str, limit: int = 60) -> list[dict]:
        """날짜별 마지막 스냅샷 = 그날 마감 누적."""
        rows = self._rows(
            """SELECT s.* FROM snapshots s
               JOIN (SELECT MAX(ts) AS mts FROM snapshots WHERE market=:m GROUP BY substr(ts,1,10)) x
                 ON s.ts = x.mts
               WHERE s.market = :m
               ORDER BY s.ts DESC LIMIT :n""",
            m=market, n=limit,
        )
        return list(reversed(rows))

    def ping(self) -> bool:
        with self.engine.connect() as c:
            c.execute(text("SELECT 1"))
        return True

    def csv(self, market: str, day: str) -> str:
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["시각", "지수", "외국인(억)", "기관(억)", "개인(억)", "기타법인(억)"])
        for r in self.day(market, day):
            w.writerow([r["ts"][11:19], r["idx"], r["foreign_eok"], r["inst_eok"], r["indiv_eok"], r["other_corp_eok"]])
        return "﻿" + buf.getvalue()  # 엑셀 한글 깨짐 방지(BOM)
