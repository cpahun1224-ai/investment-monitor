from datetime import date, timedelta

from market_reader.grading import DayBar, grade_series, latest_summary
from market_reader.rules import RuleConfig


def make_bars(closes, foreign=None, start=date(2026, 8, 1)):
    """주말을 건너뛰며 거래일을 만든다."""
    bars, d = [], start
    for k, c in enumerate(closes):
        while d.weekday() >= 5:
            d += timedelta(days=1)
        f = foreign[k] if foreign is not None else 100.0
        bars.append(DayBar(d, c, f))
        d += timedelta(days=1)
    return bars


def cfg_from(bars, idx, grade="RED", ref=4911.28):
    return RuleConfig(reference_low=ref, start_date=bars[idx].date, start_grade=grade)


def test_break_then_fail_fires_cash_step2():
    closes = [5500.0] * 70 + [5000.0, 4869.96, 4734.0]
    bars = make_bars(closes)
    out = grade_series(bars, cfg_from(bars, 69))
    assert out[1].events[0].startswith("BREAK")
    assert out[2].events[0].startswith("CASH_STEP2")
    assert all(j.grade == "RED" for j in out)
    s = latest_summary(out, cfg_from(bars, 69))
    assert any("현금 복구 2단계" in a for a in s["cio_agenda"])
    assert any("기준 저점 갱신" in a for a in s["cio_agenda"])


def test_break_then_recover_no_cash_step2():
    closes = [5500.0] * 70 + [4900.0, 4950.0]
    bars = make_bars(closes)
    out = grade_series(bars, cfg_from(bars, 69))
    assert out[0].events[0].startswith("BREAK")
    assert "회복" in out[1].events[0]
    assert not any(e.startswith("CASH_STEP2") for j in out for e in j.events)


def test_red_to_orange_requires_all_four():
    # 하락 후 저점을 높이며 회복 → 20일선 돌파 2일
    closes = [5600 - i * 10 for i in range(60)] + [5000 + i * 15 for i in range(30)]
    foreign = [100.0] * len(closes)
    bars = make_bars(closes, foreign)
    out = grade_series(bars, cfg_from(bars, 59))
    assert any(j.grade == "ORANGE" for j in out)
    first = next(j for j in out if j.grade == "ORANGE")
    assert any(e.startswith("UPGRADE: RED→ORANGE") for e in first.events)

    # 같은 가격 흐름인데 외국인이 2일 합계 마이너스면 승격 안 됨
    foreign_neg = [-100.0] * len(closes)
    out2 = grade_series(make_bars(closes, foreign_neg), cfg_from(bars, 59))
    assert all(j.grade == "RED" for j in out2)
    assert out2[-1].upgrade_checks[3].ok is False


def test_missing_foreign_data_blocks_upgrade():
    closes = [5600 - i * 10 for i in range(60)] + [5000 + i * 15 for i in range(30)]
    foreign = [None] * len(closes)
    bars = make_bars(closes, foreign)
    out = grade_series(bars, cfg_from(bars, 59))
    assert all(j.grade == "RED" for j in out)
    assert out[-1].upgrade_checks[3].ok is None  # 미확인은 통과로 세지 않음


def test_orange_downgrade_after_two_failed_days():
    closes = [6000.0] * 70 + [5800.0, 5790.0, 5780.0]
    bars = make_bars(closes)
    out = grade_series(bars, cfg_from(bars, 69, grade="ORANGE"))
    grades = [j.grade for j in out]
    assert grades == ["ORANGE", "ORANGE", "RED"]
    assert out[2].events[0].startswith("DOWNGRADE")


def test_orange_recovery_within_two_days_no_downgrade():
    closes = [6000.0] * 70 + [5800.0, 6100.0, 6100.0]
    bars = make_bars(closes)
    out = grade_series(bars, cfg_from(bars, 69, grade="ORANGE"))
    assert all(j.grade == "ORANGE" for j in out)


def test_orange_to_yellow_and_green():
    closes = [5500.0] * 60 + [5500 + i * 40 for i in range(1, 40)]
    bars = make_bars(closes)
    out = grade_series(bars, cfg_from(bars, 59, grade="ORANGE"))
    seen = [j.grade for j in out]
    assert "YELLOW" in seen
    assert seen[-1] == "GREEN"
    # YELLOW는 6,000 종가 돌파 전에는 나오면 안 됨
    first_y = next(j for j in out if j.grade == "YELLOW")
    assert first_y.close > 6000
