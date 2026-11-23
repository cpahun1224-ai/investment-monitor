from datetime import date, datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient

import market_reader.api as api
from market_reader.sources import DailyRow
from market_reader.store import get_engine
from tests.test_grading import make_bars


class FakeSource:
    name = "fake"

    def fetch(self, start, end):
        closes = [5500.0] * 80 + [5000.0, 4869.96, 4734.0]
        return [DailyRow(b.date, b.close, -1500.0, source="fake") for b in make_bars(closes)]


def client(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "_engine", get_engine(f"sqlite:///{tmp_path}/t.db"))
    monkeypatch.setattr(api, "PykrxSource", FakeSource)
    monkeypatch.setenv("MARKET_READER_TOKEN", "secret")
    bars = make_bars([1] * 80)
    monkeypatch.setenv("MR_START_DATE", bars[79].date.isoformat())
    app = FastAPI()
    app.include_router(api.router)
    return TestClient(app)


def test_collect_requires_token(tmp_path, monkeypatch):
    c = client(tmp_path, monkeypatch)
    assert c.post("/api/market/collect").status_code == 401
    r = c.post("/api/market/collect", headers={"X-Admin-Token": "secret"})
    assert r.status_code == 200
    s = r.json()["summary"]
    assert s["latest"]["grade"] == "RED"
    assert s["latest"]["budget_ratio"] == 0.0
    assert any(e.startswith("CASH_STEP2") for e in s["latest"]["events"])
    assert s["data_quality"]["ma60_history_ok"] is True


def test_manual_overrides_day(tmp_path, monkeypatch):
    c = client(tmp_path, monkeypatch)
    c.post("/api/market/collect", headers={"X-Admin-Token": "secret"})
    last = c.get("/api/market/grade").json()["as_of"]
    r = c.post(
        "/api/market/manual",
        headers={"X-Admin-Token": "secret"},
        json={"date": last, "close": 4950.0, "foreign_net_eok": 300},
    )
    latest = r.json()["latest"]
    assert latest["close"] == 4950.0
    assert not any(e.startswith("CASH_STEP2") for e in latest["events"])
    assert len(c.get("/api/market/history").json()) >= 2


def test_next_run_skips_weekend():
    fri_evening = datetime(2026, 11, 20, 19, 0, tzinfo=api.KST)
    nxt = api._next_run(fri_evening)
    assert nxt.date() == date(2026, 11, 23) and nxt.hour == 16
