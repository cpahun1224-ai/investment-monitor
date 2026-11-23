"""저장소. DATABASE_URL이 없으면 로컬 SQLite.

Railway는 컨테이너 디스크가 재배포 때 지워지므로, 운영에서는 Railway Postgres의 DATABASE_URL을 쓴다.
"""
from __future__ import annotations

import json
import os
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Float,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    select,
)
from sqlalchemy.engine import Engine

from .sources import DailyRow

metadata = MetaData()

market_daily = Table(
    "mr_market_daily",
    metadata,
    Column("date", Date, primary_key=True),
    Column("close", Float, nullable=False),
    Column("foreign_net_eok", Float),
    Column("inst_net_eok", Float),
    Column("indiv_net_eok", Float),
    Column("source", String(32)),
    Column("updated_at", DateTime(timezone=True)),
)

grade_log = Table(
    "mr_grade_log",
    metadata,
    Column("date", Date, primary_key=True),
    Column("grade", String(8), nullable=False),
    Column("prev_grade", String(8), nullable=False),
    Column("reference_low", Float, nullable=False),
    Column("payload", Text, nullable=False),  # DayJudgement.to_dict() JSON
    Column("updated_at", DateTime(timezone=True)),
)


def _normalize_url(url: str) -> str:
    # Railway/Heroku 형식 postgres:// → SQLAlchemy 형식
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://") :]
    return url


def get_engine(url: Optional[str] = None) -> Engine:
    # 기본값: 기존 앱과 같은 SQLite 파일(DATABASE_PATH). Postgres를 쓰면 DATABASE_URL이 우선한다.
    default = f"sqlite:///{os.getenv('DATABASE_PATH', './investment.db')}"
    url = _normalize_url(url or os.getenv("DATABASE_URL") or default)
    engine = create_engine(url, future=True, pool_pre_ping=True)
    metadata.create_all(engine)
    return engine


def _now():
    return datetime.now(timezone.utc)


def _upsert(engine: Engine, table: Table, key: date, values: dict) -> None:
    with engine.begin() as conn:
        exists = conn.execute(select(table.c.date).where(table.c.date == key)).first()
        if exists:
            conn.execute(table.update().where(table.c.date == key).values(**values))
        else:
            conn.execute(table.insert().values(date=key, **values))


def upsert_daily(engine: Engine, rows: list[DailyRow]) -> int:
    for r in rows:
        _upsert(
            engine,
            market_daily,
            r.date,
            dict(
                close=r.close,
                foreign_net_eok=r.foreign_net_eok,
                inst_net_eok=r.inst_net_eok,
                indiv_net_eok=r.indiv_net_eok,
                source=r.source,
                updated_at=_now(),
            ),
        )
    return len(rows)


def load_daily(engine: Engine) -> list[DailyRow]:
    with engine.connect() as conn:
        res = conn.execute(select(market_daily).order_by(market_daily.c.date)).mappings().all()
    return [
        DailyRow(
            date=r["date"],
            close=r["close"],
            foreign_net_eok=r["foreign_net_eok"],
            inst_net_eok=r["inst_net_eok"],
            indiv_net_eok=r["indiv_net_eok"],
            source=r["source"] or "",
        )
        for r in res
    ]


def save_grades(engine: Engine, judgements, reference_low: float) -> None:
    for j in judgements:
        _upsert(
            engine,
            grade_log,
            j.date,
            dict(
                grade=j.grade,
                prev_grade=j.prev_grade,
                reference_low=reference_low,
                payload=json.dumps(j.to_dict(), ensure_ascii=False),
                updated_at=_now(),
            ),
        )


def load_grades(engine: Engine, limit: int = 60) -> list[dict]:
    with engine.connect() as conn:
        res = (
            conn.execute(select(grade_log).order_by(grade_log.c.date.desc()).limit(limit))
            .mappings()
            .all()
        )
    return [json.loads(r["payload"]) for r in reversed(res)]
