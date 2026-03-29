"""
Google Gemini API 기반 투자전략 분석 모듈
모델: gemini-2.0-flash (무료 티어)
"""
import os
import json
import re
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
MODEL_NAME = "gemini-2.0-flash"

_client = None
if GEMINI_API_KEY and GEMINI_API_KEY.strip():
    _client = genai.Client(api_key=GEMINI_API_KEY)


SYSTEM_PROMPT = """당신은 20년 경력의 한국 주식 애널리스트입니다.
투자자의 보유 현황과 시장 정보를 바탕으로 실용적인 투자전략을 제시합니다.
답변은 반드시 JSON 형식으로만 반환하세요. JSON 외 다른 텍스트는 절대 포함하지 마세요."""


def build_analysis_prompt(stock: dict, context: dict) -> str:
    """분석 프롬프트 생성"""
    news_text = "\n".join([
        f"- {n['title']} ({n['date'][:10] if n.get('date') else ''})"
        for n in context.get("news", [])[:10]
    ]) or "뉴스 없음"

    disc_text = "\n".join([
        f"- [{d.get('type','')}] {d['title']} ({d.get('date','')})"
        for d in context.get("disclosures", [])[:5]
    ]) or "공시 없음"

    md = context.get("market_data", {})
    analyst_target = md.get("analyst_target", "정보 없음")
    analyst_opinion = md.get("analyst_opinion", "정보 없음")
    per = md.get("per", "N/A")
    pbr = md.get("pbr", "N/A")
    roe = md.get("roe", "N/A")

    profit_rate = 0.0
    if stock.get("avg_buy_price", 0) > 0:
        profit_rate = (stock["current_price"] - stock["avg_buy_price"]) / stock["avg_buy_price"] * 100

    return f"""{SYSTEM_PROMPT}

[종목 정보]
종목명: {stock['name']}
티커: {stock['ticker']}
현재가: {int(stock['current_price']):,}원
평균매수가: {int(stock.get('avg_buy_price', 0)):,}원
보유수량: {stock['quantity']}주
현재 수익률: {profit_rate:.1f}%
투자 단계: {stock.get('stage', '씨앗')}
목표가: {int(stock.get('target_price', 0)):,}원
손절가: {int(stock.get('stop_loss_price', 0)):,}원
섹터: {stock.get('sector', '')}

[최근 뉴스]
{news_text}

[최근 공시]
{disc_text}

[밸류에이션]
애널리스트 목표주가: {analyst_target}원
투자의견: {analyst_opinion}
PER: {per} / PBR: {pbr} / ROE: {roe}

[분석 요청]
다음 JSON 형식으로만 분석해주세요 (JSON만, 다른 텍스트 없이):
{{
  "signal": "GOOD 또는 WATCH 또는 RISK",
  "signal_reason": "신호 판단 근거 1줄",
  "market_summary": "시장 및 뉴스 요약 2-3줄",
  "analyst_view": "애널리스트 목표주가 및 의견 요약 (없으면 기술적 분석으로 대체)",
  "strategy": {{
    "short_term": "단기(1개월) 전략",
    "mid_term": "중기(3개월) 전략",
    "action": "매수강화 또는 유지 또는 부분매도 또는 전량매도",
    "action_reason": "액션 근거"
  }},
  "risk_factors": ["리스크1", "리스크2", "리스크3"],
  "catalysts": ["상승촉매1", "상승촉매2"],
  "next_stage_condition": "다음 단계 진입 조건 (씨앗→에코 또는 에코→피라미딩)"
}}"""


def analyze_stock(stock: dict, context: dict) -> dict:
    """Gemini API로 종목 투자전략 분석"""
    if not _client:
        return _mock_analysis(stock)

    try:
        prompt = build_analysis_prompt(stock, context)

        response = _client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.3,
                max_output_tokens=1500,
            ),
        )

        raw = response.text.strip()
        # JSON 블록 추출 (```json ... ``` 처리)
        m = re.search(r'```(?:json)?\s*([\s\S]+?)```', raw)
        if m:
            raw = m.group(1).strip()

        result = json.loads(raw)
        return result

    except json.JSONDecodeError as e:
        print(f"[Gemini] JSON 파싱 오류: {e}")
        return _mock_analysis(stock)
    except Exception as e:
        print(f"[Gemini] API 오류: {e}")
        return _mock_analysis(stock)


def _mock_analysis(stock: dict) -> dict:
    """API 키 없을 때 규칙 기반 분석 (fallback)"""
    profit_rate = 0.0
    if stock.get("avg_buy_price", 0) > 0:
        profit_rate = (stock["current_price"] - stock["avg_buy_price"]) / stock["avg_buy_price"] * 100

    target_rate = None
    if stock.get("target_price", 0) > 0:
        target_rate = stock["current_price"] / stock["target_price"] * 100

    # 시그널 판정
    if profit_rate < -10:
        signal = "RISK"
        action = "유지"
        signal_reason = f"수익률 {profit_rate:.1f}%로 -10% 이하 손실 구간"
    elif profit_rate > 10 and (target_rate is None or target_rate < 85):
        signal = "GOOD"
        action = "유지"
        signal_reason = f"수익률 {profit_rate:.1f}%로 양호한 수익 구간"
    elif target_rate and target_rate >= 90:
        signal = "WATCH"
        action = "부분매도"
        signal_reason = f"목표가 {target_rate:.0f}% 도달, 매도 타이밍 검토"
    else:
        signal = "WATCH"
        action = "유지"
        signal_reason = f"수익률 {profit_rate:.1f}%, 추세 모니터링 필요"

    stage = stock.get("stage", "씨앗")
    next_stage = {
        "씨앗": "수익률 +5% 이상 + 모멘텀 확인 시 에코 단계 진입",
        "에코": "수익률 +15% 이상 + 섹터 강세 확인 시 피라미딩 단계 진입",
        "피라미딩": "목표가 90% 도달 시 단계별 익절 검토",
    }.get(stage, "다음 단계 조건 검토 필요")

    return {
        "signal": signal,
        "signal_reason": signal_reason,
        "market_summary": f"{stock['name']} 현재 {profit_rate:+.1f}% 수익률. Gemini API 키 미설정으로 규칙 기반 분석 적용.",
        "analyst_view": "API 키 미설정 — .env 파일에 GEMINI_API_KEY를 입력하면 AI 분석이 활성화됩니다.",
        "strategy": {
            "short_term": f"현재 {profit_rate:+.1f}% 수준 유지, 추가 데이터 모니터링",
            "mid_term": f"목표가 {int(stock.get('target_price', 0)):,}원 달성 여부 확인",
            "action": action,
            "action_reason": signal_reason,
        },
        "risk_factors": [
            "시장 전반적 변동성 확대 위험",
            "섹터 내 경쟁 심화 위험",
            "글로벌 매크로 환경 변화",
        ],
        "catalysts": [
            "실적 개선 및 가이던스 상향 조정",
            "섹터 내 수급 개선",
        ],
        "next_stage_condition": next_stage,
    }
