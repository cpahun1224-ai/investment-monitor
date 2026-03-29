"""
네이버 금융 실시간 시세 수집 모듈
"""
import requests
import re
from datetime import datetime, time as dtime
from typing import Optional

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": "https://finance.naver.com/",
    "Accept-Language": "ko-KR,ko;q=0.9",
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)


def is_market_open() -> bool:
    """한국 장 시간 여부 (09:00~15:30, 평일)"""
    now = datetime.now()
    if now.weekday() >= 5:  # 토·일
        return False
    t = now.time()
    return dtime(9, 0) <= t <= dtime(15, 30)


def fetch_price_naver_polling(ticker: str) -> Optional[int]:
    """
    네이버 금융 polling API로 현재가 조회
    https://polling.finance.naver.com/api/realtime/domestic/stock/{ticker}
    """
    try:
        url = f"https://polling.finance.naver.com/api/realtime/domestic/stock/{ticker}"
        r = SESSION.get(url, timeout=5)
        if r.status_code == 200:
            data = r.json()
            # 응답 구조: {"datas": [{"closePrice": 176800, ...}]}
            datas = data.get("datas", [])
            if datas:
                price = datas[0].get("closePrice") or datas[0].get("stockPrice")
                if price:
                    return int(price)
    except Exception:
        pass
    return None


def fetch_price_naver_sise(ticker: str) -> Optional[int]:
    """
    네이버 금융 sise 페이지에서 현재가 스크래핑 (fallback)
    """
    try:
        url = f"https://finance.naver.com/item/sise.naver?code={ticker}"
        r = SESSION.get(url, timeout=5)
        if r.status_code == 200:
            # <dd><span id="_nowVal">176,800</span>
            m = re.search(r'id="_nowVal"[^>]*>([\d,]+)<', r.text)
            if m:
                return int(m.group(1).replace(",", ""))
    except Exception:
        pass
    return None


def fetch_price(ticker: str) -> Optional[int]:
    """polling API 우선, 실패 시 sise 스크래핑"""
    price = fetch_price_naver_polling(ticker)
    if price and price > 0:
        return price
    return fetch_price_naver_sise(ticker)


def fetch_all_prices(tickers: list[str]) -> dict[str, Optional[int]]:
    """여러 종목 시세 일괄 조회"""
    result = {}
    for ticker in tickers:
        result[ticker] = fetch_price(ticker)
    return result
