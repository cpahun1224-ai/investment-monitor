"""투자위원회용 요약 — 경자가 위원회 직전에 읽는 숫자.

공개 KRX 시장 데이터(지수·투자자별 누적 순매수)만 담는다. 계좌·보유 정보는 없다.
"""
from __future__ import annotations

from typing import Optional

CHECKPOINTS = ["09:30", "10:30", "11:30", "13:00", "14:00", "15:00", "15:30"]
FLOW_KEYS = {"foreign_eok": "외국인", "inst_eok": "기관", "indiv_eok": "개인"}


def _at(rows: list[dict], hhmm: str) -> Optional[dict]:
    """그 시각까지의 마지막 스냅샷."""
    cand = [r for r in rows if r["ts"][11:16] <= hhmm]
    return cand[-1] if cand else None


def _slim(r: Optional[dict]) -> Optional[dict]:
    if not r:
        return None
    return {"time": r["ts"][11:19], "index": r["idx"], "외국인": r["foreign_eok"], "기관": r["inst_eok"], "개인": r["indiv_eok"]}


def _change(rows: list[dict], key: str, minutes: int) -> Optional[float]:
    if len(rows) < 2 or rows[-1][key] is None:
        return None
    last = rows[-1]
    h, m = int(last["ts"][11:13]), int(last["ts"][14:16])
    t = h * 60 + m - minutes
    ref = _at(rows, f"{t // 60:02d}:{t % 60:02d}")
    if not ref or ref[key] is None:
        return None
    return round(last[key] - ref[key], 1)


def summarize(rows: list[dict], prev_close: Optional[dict], market: str) -> dict:
    if not rows:
        return {"market": market, "status": "no_data"}
    last, first = rows[-1], rows[0]
    out: dict = {
        "market": market,
        "status": "ok",
        "as_of": last["ts"],
        "is_close": last["ts"][11:16] >= "15:30",
        "rows": len(rows),
        "latest": _slim(last),
        "checkpoints": {cp: _slim(_at(rows, cp)) for cp in CHECKPOINTS if _at(rows, cp)},
    }
    # 지수: 장 초반 KRX가 지수 행을 늦게 주면 idx가 비어 있을 수 있다 → 마지막으로 받은 지수 사용
    idx_rows = [r for r in rows if r["idx"] is not None]
    if not idx_rows:
        out["index_note"] = "KRX 지수 값 아직 없음(수급만 수집 중)"
    if prev_close and prev_close.get("idx") and idx_rows:
        pc, cur_idx = prev_close["idx"], idx_rows[-1]["idx"]
        out["index_vs_prev_close"] = {"prev_close": pc, "chg": round(cur_idx - pc, 2), "pct": round((cur_idx / pc - 1) * 100, 2),
                                      "as_of": idx_rows[-1]["ts"][11:19]}
    # 투자자별: 장중 고점·저점, 최근 30·60분 변화, 방향 반전
    flows = {}
    for k, name in FLOW_KEYS.items():
        vals = [(r["ts"][11:19], r[k]) for r in rows if r[k] is not None]
        if not vals:
            continue
        hi = max(vals, key=lambda x: x[1])
        lo = min(vals, key=lambda x: x[1])
        cur = vals[-1][1]
        f = {
            "now": cur,
            "intraday_high": {"value": hi[1], "time": hi[0]},
            "intraday_low": {"value": lo[1], "time": lo[0]},
            "chg_30m": _change(rows, k, 30),
            "chg_60m": _change(rows, k, 60),
        }
        if hi[1] > 0 and cur < 0 and hi[0] < vals[-1][0]:
            f["reversal"] = f"장중 +{hi[1]:,.0f}억({hi[0][:5]})에서 순매도 {cur:,.0f}억으로 전환"
        elif lo[1] < 0 and cur > 0 and lo[0] < vals[-1][0]:
            f["reversal"] = f"장중 {lo[1]:,.0f}억({lo[0][:5]})에서 순매수 +{cur:,.0f}억으로 전환"
        flows[name] = f
    out["flows"] = flows
    # 괴리: 최근 60분 지수와 외국인 방향이 반대
    d_idx = _change(rows, "idx", 60)
    d_fr = _change(rows, "foreign_eok", 60)
    if d_idx is not None and d_fr is not None and abs(d_fr) >= 300:
        if d_idx > 0 and d_fr < 0:
            out["divergence_60m"] = f"지수 +{d_idx:.2f}p 상승 중 외국인 {d_fr:,.0f}억 순매도 확대"
        elif d_idx < 0 and d_fr > 0:
            out["divergence_60m"] = f"지수 {d_idx:.2f}p 하락 중 외국인 +{d_fr:,.0f}억 순매수"
    # 05-A ORANGE 조건 ④: 확인 2거래일 외국인 순매수 합계 (오늘 + 전일 마감)
    if prev_close and prev_close.get("foreign_eok") is not None and last["foreign_eok"] is not None:
        s = round(prev_close["foreign_eok"] + last["foreign_eok"], 1)
        out["orange_cond4_foreign_2d"] = {
            "prev_day": prev_close["ts"][:10],
            "prev_foreign": prev_close["foreign_eok"],
            "today_foreign": last["foreign_eok"],
            "sum": s,
            "positive": s > 0,
            "note": "장중 값이면 잠정. 판정은 15:30 마감 누적으로",
        }
    out["source"] = "KRX 정보데이터시스템(pykrx), 30초 수집"
    return out
