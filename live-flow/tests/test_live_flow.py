import importlib
from datetime import datetime

from fastapi.testclient import TestClient

from live_flow.collector import KST, Snapshot, is_collect_time


def make_app(tmp_path, monkeypatch, password=None):
    monkeypatch.setenv("LIVE_FLOW_DB", str(tmp_path / "t.db"))
    if password:
        monkeypatch.setenv("LIVE_FLOW_PASSWORD", password)
    else:
        monkeypatch.delenv("LIVE_FLOW_PASSWORD", raising=False)
    import live_flow.app as app_mod
    app_mod = importlib.reload(app_mod)
    calls = {"n": 0}

    def fake(market, now=None):
        calls["n"] += 1
        return Snapshot(now.isoformat(timespec="seconds"), market, 4700.0 + calls["n"], -2600.0 - calls["n"], 2700.0, -3200.0, 100.0)

    monkeypatch.setattr(app_mod, "fetch_snapshot", fake)
    return app_mod


def test_collect_and_query(tmp_path, monkeypatch):
    m = make_app(tmp_path, monkeypatch)
    for s in (0, 30):
        m.collect_once(datetime(2026, 11, 23, 13, 40, s, tzinfo=KST))
    c = TestClient(m.app)
    r = c.get("/api/day", params={"market": "KOSPI", "date": "2026-11-23"}).json()
    assert len(r["rows"]) == 2 and r["rows"][-1]["foreign_eok"] < r["rows"][0]["foreign_eok"]
    assert c.get("/api/days").json() == ["2026-11-23"]
    csv = c.get("/api/csv", params={"date": "2026-11-23"}).text
    assert "외국인(억)" in csv and "13:40:30" in csv
    assert len(c.get("/api/daily").json()) == 1
    assert c.get("/").status_code == 200


def test_password_required(tmp_path, monkeypatch):
    m = make_app(tmp_path, monkeypatch, password="pw123")
    c = TestClient(m.app)
    assert c.get("/api/days").status_code == 401
    assert c.get("/api/days", auth=("jihun", "pw123")).status_code == 200


def test_collect_error_recorded(tmp_path, monkeypatch):
    m = make_app(tmp_path, monkeypatch)
    monkeypatch.setattr(m, "fetch_snapshot", lambda market, now=None: (_ for _ in ()).throw(ConnectionError("차단")))
    assert m.collect_once(datetime(2026, 11, 23, 10, 0, tzinfo=KST)) == 0
    assert "차단" in m.status["last_error"]


def test_collect_window():
    assert is_collect_time(datetime(2026, 11, 23, 9, 0, tzinfo=KST))
    assert is_collect_time(datetime(2026, 11, 23, 15, 35, tzinfo=KST))
    assert not is_collect_time(datetime(2026, 11, 23, 15, 36, tzinfo=KST))
    assert not is_collect_time(datetime(2026, 11, 22, 10, 0, tzinfo=KST))  # 일요일
