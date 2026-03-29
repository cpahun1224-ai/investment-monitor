"""
거래내역서 PDF 파싱 → 평균매수가 계산 → DB 업데이트
"""
import pdfplumber
import re
import json
from collections import defaultdict
from database import SessionLocal
from models import Stock, Transaction

PDF_PATHS = [
    "/home/jihuny/거래내역서_20250329_20260328_1.pdf",  # 2025.03.29 ~ 2025.09.09
    "/home/jihuny/거래내역서_20250329_20260328_2.pdf",  # 2025.11.05 ~ 2026.03.28
]

# 현재 보유 종목 티커 목록 (코드 앞 A 제거)
TARGET_TICKERS = {
    "000660", "005930", "009150", "010130", "166090",
    "101490", "218410", "439260", "195940", "448900",
    "340570", "207940", "010950", "003230",
}


def parse_number(s: str) -> int:
    """쉼표 제거 후 정수 변환"""
    try:
        return int(s.replace(",", "").replace(" ", ""))
    except:
        return 0


def extract_ticker(name_code: str) -> str | None:
    """'종목명(A000660)' 형태에서 티커 추출"""
    m = re.search(r'\(A(\d{6})\)', name_code)
    if m:
        return m.group(1)
    return None


def extract_stock_name(name_code: str) -> str:
    """'종목명(A000660)' 형태에서 종목명 추출"""
    return re.sub(r'\(A\d{6}\)', '', name_code).strip()


def parse_pdf(pdf_path: str) -> list[dict]:
    """PDF에서 거래내역 파싱 (구매/판매만)"""
    transactions = []

    # 컬럼 순서:
    # 거래일자 거래구분 종목명(종목코드) 거래수량 거래대금 단가 수수료 거래세 제세금 변제/연체합 잔고 잔액
    col_pattern = re.compile(
        r'^(\d{4}\.\d{2}\.\d{2})\s+'   # 거래일자
        r'(구매|판매)\s+'               # 거래구분
        r'(.+?\(A\d{6}\))\s+'          # 종목명(코드)
        r'([\d,]+)\s+'                 # 거래수량
        r'([\d,]+)\s+'                 # 거래대금
        r'([\d,]+)\s+'                 # 단가
    )

    with pdfplumber.open(pdf_path) as pdf:
        total = len(pdf.pages)
        print(f"총 {total}페이지 파싱 중...")

        for page_num, page in enumerate(pdf.pages):
            text = page.extract_text()
            if not text:
                continue

            lines = text.split('\n')
            i = 0
            while i < len(lines):
                line = lines[i].strip()

                # 줄이 중간에 잘려 다음 줄에 이어지는 경우 합치기
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    # 다음 줄이 날짜나 헤더로 시작하지 않으면 현재 줄에 붙이기
                    if (re.match(r'^\d{4}\.\d{2}\.\d{2}', line) and
                            not re.match(r'^\d{4}\.\d{2}\.\d{2}', next_line) and
                            not re.match(r'^(거래일자|수량단위|원화|달러|발급)', next_line)):
                        line = line + ' ' + next_line
                        i += 1

                m = col_pattern.match(line)
                if m:
                    date_str = m.group(1)
                    txn_type = m.group(2)
                    name_code = m.group(3)
                    quantity = parse_number(m.group(4))
                    amount = parse_number(m.group(5))
                    price = parse_number(m.group(6))

                    ticker = extract_ticker(name_code)
                    stock_name = extract_stock_name(name_code)

                    if ticker:
                        transactions.append({
                            "date": date_str,
                            "type": txn_type,
                            "ticker": ticker,
                            "name": stock_name,
                            "quantity": quantity,
                            "price": price,
                            "amount": amount,
                        })
                i += 1

    return transactions


def calc_avg_buy_price(transactions: list[dict], ticker: str) -> dict:
    """
    특정 티커의 평균매수가 계산 (가중평균법)
    매도 시 비율만큼 제거 (FIFO 대신 평균단가 유지 방식)
    """
    total_qty = 0
    total_cost = 0.0

    txns = sorted(
        [t for t in transactions if t["ticker"] == ticker],
        key=lambda x: x["date"]
    )

    for t in txns:
        if t["type"] == "구매":
            total_cost += t["price"] * t["quantity"]
            total_qty += t["quantity"]
        elif t["type"] == "판매":
            if total_qty > 0:
                # 평균단가 유지하며 수량만 감소
                avg = total_cost / total_qty
                total_qty -= t["quantity"]
                total_cost = avg * max(total_qty, 0)
                if total_qty < 0:
                    total_qty = 0
                    total_cost = 0

    avg_price = total_cost / total_qty if total_qty > 0 else 0
    return {
        "ticker": ticker,
        "qty": total_qty,
        "avg_buy_price": round(avg_price),
        "total_cost": round(total_cost),
    }


def update_db(results: list[dict]):
    """계산 결과를 DB에 반영"""
    db = SessionLocal()
    try:
        updated = []
        for r in results:
            if r["avg_buy_price"] == 0:
                continue
            stock = db.query(Stock).filter(Stock.ticker == r["ticker"]).first()
            if stock:
                old = stock.avg_buy_price
                stock.avg_buy_price = float(r["avg_buy_price"])
                db.commit()
                updated.append(f"  {stock.name}({r['ticker']}): {int(old):,}원 → {r['avg_buy_price']:,}원")
        return updated
    finally:
        db.close()


def update_transactions_db(transactions: list[dict]):
    """전체 거래내역을 DB에 저장 (기존 초기데이터 대체)"""
    db = SessionLocal()
    try:
        # 기존 거래내역 전체 삭제
        db.query(Transaction).delete()
        db.commit()

        for t in transactions:
            txn = Transaction(
                ticker=t["ticker"],
                stock_name=t["name"],
                transaction_type="매수" if t["type"] == "구매" else "매도",
                quantity=t["quantity"],
                price=t["price"],
                amount=t["amount"],
                memo="PDF 파싱",
            )
            db.add(txn)
        db.commit()
        print(f"  거래내역 {len(transactions)}건 저장 완료")
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 60)
    print("거래내역서 PDF 파싱 시작 (PDF1 + PDF2 합산)")
    print("=" * 60)

    # 1. 두 PDF 파싱 후 날짜순 합산
    all_txns = []
    for path in PDF_PATHS:
        print(f"\n[파싱] {path.split('/')[-1]}")
        txns = parse_pdf(path)
        print(f"  → {len(txns)}건 파싱")
        all_txns.extend(txns)

    # 날짜순 정렬 (두 PDF가 시간순으로 이어지므로)
    all_txns.sort(key=lambda x: x["date"])
    print(f"\n총 거래내역 파싱: {len(all_txns)}건")

    # 대상 종목만 필터
    target_txns = [t for t in all_txns if t["ticker"] in TARGET_TICKERS]
    print(f"보유 종목 관련 거래: {len(target_txns)}건\n")

    # 2. 종목별 평균매수가 계산
    print("=" * 60)
    print("종목별 평균매수가 계산 결과")
    print("=" * 60)
    results = []
    for ticker in sorted(TARGET_TICKERS):
        r = calc_avg_buy_price(all_txns, ticker)
        results.append(r)
        if r["avg_buy_price"] > 0:
            print(f"  {ticker} | 잔고{r['qty']:>5}주 | 평균매수가 {r['avg_buy_price']:>10,}원")
        else:
            print(f"  {ticker} | 거래내역 없음 (0원)")

    # 3. DB 업데이트
    print("\n" + "=" * 60)
    print("DB 평균매수가 업데이트")
    print("=" * 60)
    updates = update_db(results)
    for u in updates:
        print(u)

    # 4. 전체 거래내역 DB 저장
    print("\n" + "=" * 60)
    print("전체 거래내역 DB 저장")
    print("=" * 60)
    update_transactions_db(all_txns)

    print("\n완료!")

    # 5. JSON으로도 저장
    output = {t["ticker"]: t for t in results}
    with open("/tmp/avg_buy_prices.json", "w") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print("결과 저장: /tmp/avg_buy_prices.json")
