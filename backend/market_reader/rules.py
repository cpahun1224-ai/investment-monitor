"""05 매수규칙 A절(시장 등급 정의, CIO 승인 2026-11-14)의 상수와 설정.

수치를 바꿀 때는 CIO 승인 후 환경변수로 덮어쓴다. 코드 기본값 = 승인 당시 값.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date

GRADES = ["RED", "ORANGE", "YELLOW", "GREEN"]

# 등급별 월 매수 한도(계좌 총자산 대비) — 05 문서 B 규칙 1
MONTHLY_BUY_BUDGET = {"RED": 0.0, "ORANGE": 0.02, "YELLOW": 0.05, "GREEN": 0.10}
BUDGET_SCOPE = {
    "RED": "매도만 가능",
    "ORANGE": "씨앗 1종목만",
    "YELLOW": "씨앗·에코",
    "GREEN": "정상 진입 규칙",
}


@dataclass(frozen=True)
class RuleConfig:
    # 직전 저점(RED→ORANGE 조건 ③, RED 상태 이탈 이벤트 기준). CIO가 갱신을 승인하면 바꾼다.
    reference_low: float = 4911.28
    # ORANGE→YELLOW 조건 ②: 10월 말 매물대 상단
    yellow_breakout: float = 6000.0
    # 판정 시작일과 그날의 등급(05 문서 승인일 기준 RED)
    start_date: date = date(2026, 11, 14)
    start_grade: str = "RED"
    # 하향: 20일선 이탈 후 몇 거래일 안에 회복하지 못하면 한 단계 내릴지
    ma20_fail_days: int = 2
    # '저점 높이기' 비교 창(최근 N거래일 최저 종가 vs 그 이전 M거래일 최저 종가)
    higher_low_recent: int = 10
    higher_low_prior: int = 20

    @classmethod
    def from_env(cls) -> "RuleConfig":
        d = cls()
        start = os.getenv("MR_START_DATE")
        return cls(
            reference_low=float(os.getenv("MR_REFERENCE_LOW", d.reference_low)),
            yellow_breakout=float(os.getenv("MR_YELLOW_BREAKOUT", d.yellow_breakout)),
            start_date=date.fromisoformat(start) if start else d.start_date,
            start_grade=os.getenv("MR_START_GRADE", d.start_grade).upper(),
        )
