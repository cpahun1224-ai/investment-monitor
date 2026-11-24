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


def test_store_on_postgres_if_available():
    """LIVE_FLOW_TEST_PG에 Postgres 주소가 있으면 같은 저장 코드를 Postgres로 검증."""
    import os
    import pytest

    url = os.getenv("LIVE_FLOW_TEST_PG")
    if not url:
        pytest.skip("Postgres 테스트 주소 없음")
    from live_flow.db import Store
    from sqlalchemy import text

    st = Store(url)
    with st.engine.begin() as c:
        c.execute(text("DELETE FROM snapshots"))
    st.add(Snapshot("2026-11-20T15:35:00+09:00", "KOSPI", 4869.96, -10956.0, -9330.2, 15214.4, 0.0))
    st.add(Snapshot("2026-11-23T13:40:00+09:00", "KOSPI", 4705.4, -2666.0, 2733.0, -3243.0, 0.0))
    st.add(Snapshot("2026-11-23T13:40:30+09:00", "KOSPI", 4702.1, -2666.0, 2733.0, -3243.0, 0.0))
    st.add(Snapshot("2026-11-23T13:40:30+09:00", "KOSPI", 4702.2, -2650.0, 2733.0, -3243.0, 0.0))  # 덮어쓰기
    assert [r["idx"] for r in st.day("KOSPI", "2026-11-23")] == [4705.4, 4702.2]
    assert st.days("KOSPI") == ["2026-11-23", "2026-11-20"]
    assert [r["ts"][:10] for r in st.daily_close("KOSPI")] == ["2026-11-20", "2026-11-23"]
    assert "13:40:30" in st.csv("KOSPI", "2026-11-23") and st.ping()


def test_committee_summary(tmp_path, monkeypatch):
    m = make_app(tmp_path, monkeypatch, password="pw")
    st = m.store
    st.add(Snapshot("2026-11-20T15:35:00+09:00", "KOSPI", 4869.96, -10956.0, -9330.2, 15214.4, 0.0))
    pts = [("09:00:00", 4735.0, 500.0), ("09:30:00", 4760.0, 3015.0), ("11:00:00", 4700.0, 200.0),
           ("13:42:00", 4701.98, -2648.0), ("14:51:00", 4743.07, -798.0)]
    for t, i, f in pts:
        st.add(Snapshot(f"2026-11-23T{t}+09:00", "KOSPI", i, f, 2000.0, -3000.0, 0.0))
    c = TestClient(m.app)
    r = c.get("/api/committee", params={"date": "2026-11-23"})
    assert r.status_code == 200  # 비밀번호 없이 열림
    k = r.json()["markets"]["KOSPI"]
    assert k["latest"]["외국인"] == -798.0 and k["is_close"] is False
    assert k["flows"]["외국인"]["intraday_high"]["value"] == 3015.0
    assert "순매도" in k["flows"]["외국인"]["reversal"]
    assert k["index_vs_prev_close"]["prev_close"] == 4869.96
    assert k["orange_cond4_foreign_2d"]["positive"] is False
    assert "09:30" in k["checkpoints"]
    assert k["flows"]["외국인"]["chg_60m"] == round(-798.0 - (-2648.0), 1)


def test_summarize_survives_missing_index_early_session():
    """2026-11-24 장 초반: KRX 지수 행이 비어 idx=None → /api/committee 500 회귀 방지."""
    from live_flow.committee import summarize

    rows = [
        {"ts": "2026-11-24T09:00:30+09:00", "idx": None, "foreign_eok": 120.0, "inst_eok": -30.0, "indiv_eok": -90.0, "other_corp_eok": 0.0},
        {"ts": "2026-11-24T09:12:30+09:00", "idx": None, "foreign_eok": 800.0, "inst_eok": -100.0, "indiv_eok": -700.0, "other_corp_eok": 0.0},
    ]
    pc = {"ts": "2026-11-23T15:35:30+09:00", "idx": 4713.65, "foreign_eok": -2469.4}
    k = summarize(rows, pc, "KOSPI")
    assert k["status"] == "ok" and "index_vs_prev_close" not in k
    assert k["orange_cond4_foreign_2d"]["sum"] == round(-2469.4 + 800.0, 1)
    rows.append({"ts": "2026-11-24T09:13:00+09:00", "idx": 4900.0, "foreign_eok": 850.0, "inst_eok": -90.0, "indiv_eok": -760.0, "other_corp_eok": 0.0})
    assert summarize(rows, pc, "KOSPI")["index_vs_prev_close"]["chg"] == round(4900.0 - 4713.65, 2)
