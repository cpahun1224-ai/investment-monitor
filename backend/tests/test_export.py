import json
from datetime import date

from market_reader.export import add_manual, load_csv, run
from market_reader.rules import RuleConfig
from market_reader.sources import DailyRow
from tests.test_grading import make_bars

CLOSES = [5500.0] * 80 + [5000.0, 4869.96, 4734.0]
BARS = make_bars(CLOSES)
CFG = RuleConfig(start_date=BARS[79].date)


class FakeSource:
    name = "fake"

    def __init__(self, foreign=-1500.0, fail=False):
        self.foreign, self.fail = foreign, fail

    def fetch(self, start, end):
        if self.fail:
            raise ConnectionError("KRX 접속 차단")
        return [DailyRow(b.date, b.close, self.foreign, source="fake") for b in BARS]


def paths(tmp_path):
    return dict(csv_path=tmp_path / "daily.csv", out_dir=tmp_path / "out")


def after_close():
    from datetime import datetime
    from market_reader.export import KST

    d = BARS[-1].date
    return datetime(d.year, d.month, d.day, 20, 0, tzinfo=KST)


def read(tmp_path, name):
    return json.loads((tmp_path / "out" / name).read_text(encoding="utf-8"))


def test_export_writes_grade_and_history(tmp_path):
    assert run(FakeSource(), CFG, **paths(tmp_path), now=after_close()) is True
    g = read(tmp_path, "grade.json")
    assert g["latest"]["grade"] == "RED"
    assert any(e.startswith("CASH_STEP2") for e in g["latest"]["events"])
    assert g["collector"]["ok"] is True
    assert g["data_quality"]["ma60_history_ok"] is True
    assert len(read(tmp_path, "history.json")) == 3
    assert len(load_csv(tmp_path / "daily.csv")) == len(BARS)


def test_collector_failure_still_grades_from_csv(tmp_path):
    run(FakeSource(), CFG, **paths(tmp_path), now=after_close())
    assert run(FakeSource(fail=True), CFG, **paths(tmp_path), now=after_close()) is False
    g = read(tmp_path, "grade.json")
    assert g["collector"]["ok"] is False and "차단" in g["collector"]["error"]
    assert g["latest"]["grade"] == "RED"  # 이전 데이터로 판정은 유지


def test_manual_then_krx_fill(tmp_path):
    run(FakeSource(), CFG, **paths(tmp_path), now=after_close())
    last = BARS[-1].date
    add_manual(DailyRow(last, 4950.0, 300.0), tmp_path / "daily.csv")
    run(None, CFG, **paths(tmp_path), now=after_close())
    g = read(tmp_path, "grade.json")
    assert g["latest"]["close"] == 4950.0
    assert last.isoformat() in g["data_quality"]["manual_days"]
    # 나중에 KRX가 외국인 칸을 비워 주면 수동값을 남긴다
    run(FakeSource(foreign=None), CFG, **paths(tmp_path), now=after_close())
    assert load_csv(tmp_path / "daily.csv")[last].foreign_net_eok == 300.0


def test_intraday_run_drops_today(tmp_path):
    from datetime import datetime
    from market_reader.export import KST

    last = BARS[-1].date
    noon = datetime(last.year, last.month, last.day, 13, 38, tzinfo=KST)
    run(FakeSource(), CFG, **paths(tmp_path), now=noon)
    assert last not in load_csv(tmp_path / "daily.csv")
    g = read(tmp_path, "grade.json")
    assert g["as_of"] == BARS[-2].date.isoformat() and g["collector"]["intraday_skipped"] is True
    after = datetime(last.year, last.month, last.day, 16, 10, tzinfo=KST)
    run(FakeSource(), CFG, **paths(tmp_path), now=after)
    assert last in load_csv(tmp_path / "daily.csv")
