"""시장 등급 판정 엔진 (05 문서 A절).

입력: 날짜순 일봉(종가, 외국인 현물 순매수 억원). 출력: 날짜별 등급, 조건 점검표, 이벤트.
외부 I/O가 없는 순수 함수라서 저장소·수집기와 따로 테스트한다.

규칙을 해석한 지점(주석 [해석])은 CIO 확인이 필요하면 README의 '해석 목록'에 같이 적어 둔다.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Optional

from .rules import BUDGET_SCOPE, GRADES, MONTHLY_BUY_BUDGET, RuleConfig


@dataclass
class DayBar:
    date: date
    close: float
    foreign_net_eok: Optional[float] = None  # 유가증권시장 외국인 현물 순매수(억원)


@dataclass
class Check:
    name: str
    ok: Optional[bool]  # None = 데이터 부족으로 판정 불가
    detail: str


@dataclass
class DayJudgement:
    date: date
    close: float
    ma20: Optional[float]
    ma60: Optional[float]
    foreign_net_eok: Optional[float]
    grade: str
    prev_grade: str
    events: list[str] = field(default_factory=list)
    upgrade_target: Optional[str] = None
    upgrade_checks: list[Check] = field(default_factory=list)
    downgrade_watch: list[Check] = field(default_factory=list)

    @property
    def budget_ratio(self) -> float:
        return MONTHLY_BUY_BUDGET[self.grade]

    def to_dict(self) -> dict:
        d = asdict(self)
        d["date"] = self.date.isoformat()
        d["budget_ratio"] = self.budget_ratio
        d["budget_scope"] = BUDGET_SCOPE[self.grade]
        return d


def _ma(closes: list[float], i: int, n: int) -> Optional[float]:
    if i + 1 < n:
        return None
    return sum(closes[i + 1 - n : i + 1]) / n


def _fmt(x: Optional[float]) -> str:
    return "미확인" if x is None else f"{x:,.2f}"


def grade_series(bars: list[DayBar], cfg: RuleConfig | None = None) -> list[DayJudgement]:
    """cfg.start_date 이후 거래일마다 등급을 판정해 돌려준다.

    이동평균은 start_date 이전 데이터까지 써서 계산하므로, 최소 60거래일 이전부터 넣어야 한다.
    """
    cfg = cfg or RuleConfig()
    bars = sorted(bars, key=lambda b: b.date)
    closes = [b.close for b in bars]
    ma20 = [_ma(closes, i, 20) for i in range(len(bars))]
    ma60 = [_ma(closes, i, 60) for i in range(len(bars))]

    grade = cfg.start_grade
    below_ma20_run = 0  # 상위 등급에서 20일선 아래 연속 종가 수
    break_pending = False  # RED에서 기준 저점 종가 이탈 후 다음 날 판정 대기
    out: list[DayJudgement] = []

    for i, bar in enumerate(bars):
        if bar.date <= cfg.start_date:
            continue
        prev_grade = grade
        events: list[str] = []
        c, m20, m60 = bar.close, ma20[i], ma60[i]
        has_prev = i >= 1
        pc = closes[i - 1] if has_prev else None
        pm20 = ma20[i - 1] if has_prev else None
        pm60 = ma60[i - 1] if has_prev else None

        # ── 1) 하향 판정 ──────────────────────────────────────────
        if grade == "RED":
            below_ma20_run = 0
            if break_pending:
                if c < cfg.reference_low:
                    events.append(
                        f"CASH_STEP2: 기준 저점 {cfg.reference_low:,.2f} 종가 이탈 후 다음 날 회복 실패"
                        f"(종가 {c:,.2f}) → RED 유지 + 현금 복구 2단계 상정"
                    )
                else:
                    events.append(f"기준 저점 {cfg.reference_low:,.2f} 다음 날 회복(종가 {c:,.2f})")
                break_pending = False
            elif c < cfg.reference_low and (pc is None or pc >= cfg.reference_low):
                events.append(
                    f"BREAK: 기준 저점 {cfg.reference_low:,.2f} 종가 이탈(종가 {c:,.2f}). 다음 거래일 회복 여부 판정"
                )
                break_pending = True
        else:
            # 구조적 RED (세 조건 모두) — [해석] 지지선 = 기준 저점, ③은 최근 20일 고점·저점이
            # 그 이전 20일보다 모두 낮은 경우로 근사
            struct = _structural_red(closes, i, cfg)
            if struct:
                events.append("STRUCTURAL_RED: 지지 이탈 + 회복 실패 + 고점·저점 동반 하락 → 즉시 RED")
                grade = "RED"
                below_ma20_run = 0
            elif m20 is not None and c < m20:
                below_ma20_run += 1
                # 이탈일 + 이후 N거래일 모두 회복 실패 → 한 단계 하향
                if below_ma20_run >= cfg.ma20_fail_days + 1:
                    new = GRADES[GRADES.index(grade) - 1]
                    events.append(
                        f"DOWNGRADE: 20일선 이탈 후 {cfg.ma20_fail_days}거래일 내 회복 실패 → {grade}→{new}"
                    )
                    grade = new
                    below_ma20_run = 0
            else:
                below_ma20_run = 0

        # ── 2) 상향 판정 (하향이 없던 날만) ────────────────────────
        upgrade_target, checks = None, []
        if grade == prev_grade:
            if grade == "RED":
                upgrade_target = "ORANGE"
                checks = _red_to_orange(bars, closes, ma20, i, cfg)
            elif grade == "ORANGE":
                upgrade_target = "YELLOW"
                checks = _orange_to_yellow(closes, ma20, i, cfg)
            elif grade == "YELLOW":
                upgrade_target = "GREEN"
                checks = [
                    Check("① 60일선 종가 회복", None if m60 is None else c > m60, f"종가 {_fmt(c)} / 60일선 {_fmt(m60)}"),
                    Check(
                        "② 다음 거래일 종가 유지",
                        None if pm60 is None or pc is None or m60 is None else (pc > pm60 and c > m60),
                        f"전일 {_fmt(pc)} / 전일 60일선 {_fmt(pm60)}",
                    ),
                ]
            if checks and all(ch.ok is True for ch in checks):
                events.append(f"UPGRADE: {grade}→{upgrade_target} (조건 모두 충족)")
                grade = upgrade_target
                break_pending = False
                below_ma20_run = 0

        watch = []
        if grade != "RED":
            watch.append(
                Check(
                    "20일선 위 종가",
                    None if m20 is None else c >= m20,
                    f"종가 {_fmt(c)} / 20일선 {_fmt(m20)} / 이탈 연속 {below_ma20_run}일"
                    f"(이탈일 포함 {cfg.ma20_fail_days + 1}일이면 하향)",
                )
            )
        else:
            watch.append(
                Check(
                    "기준 저점 위 종가",
                    c >= cfg.reference_low,
                    f"종가 {c:,.2f} / 기준 저점 {cfg.reference_low:,.2f}",
                )
            )

        out.append(
            DayJudgement(
                date=bar.date,
                close=c,
                ma20=m20,
                ma60=m60,
                foreign_net_eok=bar.foreign_net_eok,
                grade=grade,
                prev_grade=prev_grade,
                events=events,
                upgrade_target=upgrade_target,
                upgrade_checks=checks,
                downgrade_watch=watch,
            )
        )
    return out


def _red_to_orange(bars, closes, ma20, i, cfg: RuleConfig) -> list[Check]:
    c, m20 = closes[i], ma20[i]
    pc = closes[i - 1] if i >= 1 else None
    pm20 = ma20[i - 1] if i >= 1 else None
    f_today = bars[i].foreign_net_eok
    f_prev = bars[i - 1].foreign_net_eok if i >= 1 else None

    # ③ [해석] '직전 저점 위에서 저점이 높아짐' = 확인 2거래일 종가가 기준 저점을 깨지 않고,
    #   최근 10거래일 최저 종가 > 그 이전 20거래일 최저 종가
    r, p = cfg.higher_low_recent, cfg.higher_low_prior
    if i + 1 >= r + p:
        recent_low = min(closes[i + 1 - r : i + 1])
        prior_low = min(closes[i + 1 - r - p : i + 1 - r])
        higher_low = recent_low > prior_low
        hl_detail = f"최근 {r}일 최저 {recent_low:,.2f} vs 이전 {p}일 최저 {prior_low:,.2f}"
    else:
        higher_low, hl_detail = None, "데이터 부족"
    above_ref = pc is not None and min(c, pc) >= cfg.reference_low
    cond3 = None if higher_low is None else (above_ref and higher_low)

    fsum = None if f_today is None or f_prev is None else f_today + f_prev
    return [
        Check("① 종가 20일선 위", None if m20 is None else c > m20, f"종가 {_fmt(c)} / 20일선 {_fmt(m20)}"),
        Check(
            "② 다음 거래일도 20일선 위",
            None if pm20 is None or pc is None or m20 is None else (pc > pm20 and c > m20),
            f"전일 {_fmt(pc)} / 전일 20일선 {_fmt(pm20)}",
        ),
        Check(
            "③ 기준 저점 위 저점 상승",
            cond3,
            f"2일 종가 기준 저점({cfg.reference_low:,.2f}) 위: {'예' if above_ref else '아니오'} / {hl_detail}",
        ),
        Check(
            "④ 2거래일 외국인 순매수 합계 플러스",
            None if fsum is None else fsum > 0,
            f"합계 {_fmt(fsum)}억원 (전일 {_fmt(f_prev)} / 당일 {_fmt(f_today)})",
        ),
    ]


def _orange_to_yellow(closes, ma20, i, cfg: RuleConfig) -> list[Check]:
    c = closes[i]
    seq = [ma20[i - k] for k in range(4)] if i >= 3 else [None]
    rising = None if any(x is None for x in seq) else (seq[0] > seq[1] > seq[2] > seq[3])
    return [
        Check("① 20일선 3거래일 연속 상승", rising, "20일선 " + " ← ".join(_fmt(x) for x in seq)),
        Check(
            f"② {cfg.yellow_breakout:,.0f} 종가 돌파",
            c > cfg.yellow_breakout,
            f"종가 {c:,.2f}",
        ),
    ]


def _structural_red(closes, i, cfg: RuleConfig) -> bool:
    if i < 40:
        return False
    broke = closes[i - 1] < cfg.reference_low  # ① 지지 종가 이탈
    failed = closes[i] < cfg.reference_low  # ② 회복 실패
    recent, prior = closes[i - 19 : i + 1], closes[i - 39 : i - 19]
    lower = max(recent) < max(prior) and min(recent) < min(prior)  # ③ 고점·저점 동반 하락
    return broke and failed and lower


def latest_summary(judgements: list[DayJudgement], cfg: RuleConfig | None = None) -> dict:
    """화면·알림용 요약. 기준 저점보다 낮은 새 최저 종가가 나오면 CIO 갱신 안건으로 띄운다."""
    cfg = cfg or RuleConfig()
    if not judgements:
        return {"status": "no_data"}
    last = judgements[-1]
    lowest = min(judgements, key=lambda j: j.close)
    agenda = []
    if lowest.close < cfg.reference_low:
        agenda.append(
            f"기준 저점 갱신 검토: 판정 기간 최저 종가 {lowest.close:,.2f}({lowest.date.isoformat()})가 "
            f"현재 기준 {cfg.reference_low:,.2f}보다 낮음. 갱신 전까지 ORANGE 조건 ③은 충족 불가."
        )
    if any(e.startswith("CASH_STEP2") for e in last.events):
        agenda.append("현금 복구 2단계(현금 20%) CIO 결정 필요")
    return {
        "status": "ok",
        "as_of": last.date.isoformat(),
        "reference_low": cfg.reference_low,
        "latest": last.to_dict(),
        "cio_agenda": agenda,
        "recent_events": [
            {"date": j.date.isoformat(), "events": j.events} for j in judgements[-20:] if j.events
        ],
    }
