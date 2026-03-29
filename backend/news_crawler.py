"""
뉴스/공시 수집 모듈
- 네이버 검색 API: 종목별 최근 뉴스 10건
- DART API: 최근 공시 5건
"""
import os
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID", "")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET", "")
DART_API_KEY = os.getenv("DART_API_KEY", "")

HEADERS_NAVER = {
    "X-Naver-Client-Id": NAVER_CLIENT_ID,
    "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
    "User-Agent": "Mozilla/5.0",
}


def fetch_naver_news(stock_name: str, display: int = 10) -> list[dict]:
    """네이버 검색 API로 종목 뉴스 수집"""
    if not NAVER_CLIENT_ID or NAVER_CLIENT_ID == "your_naver_client_id":
        return _fallback_naver_news(stock_name)

    try:
        url = "https://openapi.naver.com/v1/search/news.json"
        params = {
            "query": f"{stock_name} 주식",
            "display": display,
            "sort": "date",
        }
        r = requests.get(url, headers=HEADERS_NAVER, params=params, timeout=5)
        if r.status_code == 200:
            items = r.json().get("items", [])
            result = []
            for item in items:
                import re
                title = re.sub(r'<[^>]+>', '', item.get("title", ""))
                pub_date = item.get("pubDate", "")
                result.append({"title": title, "date": pub_date, "link": item.get("link", "")})
            return result
    except Exception as e:
        print(f"[뉴스] {stock_name} 조회 실패: {e}")

    return _fallback_naver_news(stock_name)


def _fallback_naver_news(stock_name: str) -> list[dict]:
    """API 키 없을 때 네이버 금융 뉴스 스크래핑 fallback"""
    try:
        from bs4 import BeautifulSoup
        # 네이버 금융 검색 (종목 이름으로)
        url = "https://finance.naver.com/search/searchList.naver"
        params = {"query": stock_name}
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        r = requests.get(url, params=params, headers=headers, timeout=5)
        if r.status_code != 200:
            return []
        soup = BeautifulSoup(r.text, "html.parser")
        items = []
        for a in soup.select("dl.newsList dt a")[:10]:
            items.append({"title": a.get_text(strip=True), "date": "", "link": a.get("href", "")})
        return items
    except Exception:
        return []


def fetch_dart_disclosures(stock_name: str, corp_code: str = None, days: int = 30) -> list[dict]:
    """DART API로 최근 공시 수집"""
    if not DART_API_KEY or DART_API_KEY == "your_dart_api_key":
        return _fallback_dart(stock_name)

    try:
        # 기업 코드 조회 (corp_code 없을 경우 회사명으로 검색)
        if not corp_code:
            corp_code = _search_dart_corp_code(stock_name)
        if not corp_code:
            return []

        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")

        url = "https://opendart.fss.or.kr/api/list.json"
        params = {
            "crtfc_key": DART_API_KEY,
            "corp_code": corp_code,
            "bgn_de": start_date,
            "end_de": end_date,
            "page_count": 5,
            "sort": "date",
            "sort_mth": "desc",
        }
        r = requests.get(url, params=params, timeout=5)
        if r.status_code == 200:
            data = r.json()
            if data.get("status") == "000":
                return [
                    {
                        "title": item.get("report_nm", ""),
                        "date": item.get("rcept_dt", ""),
                        "type": item.get("pblntf_ty_nm", ""),
                    }
                    for item in data.get("list", [])[:5]
                ]
    except Exception as e:
        print(f"[DART] {stock_name} 조회 실패: {e}")

    return _fallback_dart(stock_name)


def _search_dart_corp_code(company_name: str) -> str | None:
    """DART에서 회사명으로 corp_code 검색"""
    try:
        url = "https://opendart.fss.or.kr/api/company.json"
        params = {"crtfc_key": DART_API_KEY, "corp_name": company_name}
        r = requests.get(url, params=params, timeout=5)
        if r.status_code == 200:
            data = r.json()
            if data.get("status") == "000" and data.get("list"):
                return data["list"][0]["corp_code"]
    except Exception:
        pass
    return None


def _fallback_dart(stock_name: str) -> list[dict]:
    """DART API 없을 때 공시정보 없음 반환"""
    return []


def fetch_stock_market_data(ticker: str) -> dict:
    """네이버 금융에서 PER, PBR, ROE, 목표주가 수집 (스크래핑)"""
    try:
        import re
        from bs4 import BeautifulSoup
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

        result = {}

        # 종목 분석 페이지
        url = f"https://finance.naver.com/item/coinfo.naver?code={ticker}"
        r = requests.get(url, headers=headers, timeout=5)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")

            # PER, PBR, ROE 수집
            for td in soup.select("table.tb_type1 tr"):
                tds = td.select("td")
                ths = td.select("th")
                for th in ths:
                    text = th.get_text(strip=True)
                    idx = ths.index(th)
                    if idx < len(tds):
                        val = tds[idx].get_text(strip=True).replace(",", "")
                        if "PER" in text:
                            result["per"] = val
                        elif "PBR" in text:
                            result["pbr"] = val
                        elif "ROE" in text:
                            result["roe"] = val

        # 목표주가 수집 (증권사 컨센서스)
        url2 = f"https://finance.naver.com/item/analyst.naver?code={ticker}"
        r2 = requests.get(url2, headers=headers, timeout=5)
        if r2.status_code == 200:
            soup2 = BeautifulSoup(r2.text, "html.parser")
            # 목표주가 영역
            target_area = soup2.select_one("div.target_table")
            if target_area:
                nums = re.findall(r'[\d,]+', target_area.get_text())
                if nums:
                    result["analyst_target"] = nums[0].replace(",", "")

            # 투자의견 수집
            opinion = soup2.select_one("strong.lnk_opinion")
            if opinion:
                result["analyst_opinion"] = opinion.get_text(strip=True)

        return result
    except Exception as e:
        print(f"[시장데이터] {ticker} 조회 실패: {e}")
        return {}


def collect_stock_context(stock_name: str, ticker: str) -> dict:
    """종목 분석을 위한 모든 컨텍스트 수집"""
    news = fetch_naver_news(stock_name)
    disclosures = fetch_dart_disclosures(stock_name)
    market_data = fetch_stock_market_data(ticker)

    return {
        "news": news,
        "disclosures": disclosures,
        "market_data": market_data,
    }
