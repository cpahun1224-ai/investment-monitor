from database import SessionLocal, engine
from models import Base, Stock, Transaction, Portfolio
from datetime import datetime

INITIAL_STOCKS = [
    {"name": "SK하이닉스", "ticker": "000660", "quantity": 76, "avg_buy_price": 930000, "current_price": 922000, "sector": "반도체", "stage": "에코"},
    {"name": "삼성전자", "ticker": "005930", "quantity": 491, "avg_buy_price": 188000, "current_price": 179700, "sector": "반도체", "stage": "에코"},
    {"name": "삼성전기", "ticker": "009150", "quantity": 176, "avg_buy_price": 440000, "current_price": 434000, "sector": "반도체부품", "stage": "에코"},
    {"name": "고려아연", "ticker": "010130", "quantity": 22, "avg_buy_price": 1620000, "current_price": 1483000, "sector": "소재", "stage": "씨앗"},
    {"name": "하나머티리얼즈", "ticker": "166090", "quantity": 651, "avg_buy_price": 61500, "current_price": 63400, "sector": "반도체소재", "stage": "에코"},
    {"name": "에스앤에스텍", "ticker": "101490", "quantity": 414, "avg_buy_price": 88000, "current_price": 83500, "sector": "반도체소재", "stage": "에코"},
    {"name": "RFHIC", "ticker": "218410", "quantity": 920, "avg_buy_price": 72000, "current_price": 82400, "sector": "방산", "stage": "에코"},
    {"name": "대한조선", "ticker": "439260", "quantity": 480, "avg_buy_price": 97364, "current_price": 85700, "sector": "조선", "stage": "에코"},
    {"name": "HK이노엔", "ticker": "195940", "quantity": 201, "avg_buy_price": 50000, "current_price": 53100, "sector": "바이오", "stage": "씨앗"},
    {"name": "한국피아이엠", "ticker": "448900", "quantity": 151, "avg_buy_price": 105000, "current_price": 121000, "sector": "소재", "stage": "씨앗"},
    {"name": "티앤엘", "ticker": "340570", "quantity": 61, "avg_buy_price": 0, "current_price": 52400, "sector": "바이오", "stage": "씨앗"},
    {"name": "삼성바이오로직스", "ticker": "207940", "quantity": 2, "avg_buy_price": 0, "current_price": 1606000, "sector": "바이오", "stage": "씨앗"},
    {"name": "S-Oil", "ticker": "010950", "quantity": 1, "avg_buy_price": 0, "current_price": 109700, "sector": "에너지", "stage": "씨앗"},
    {"name": "삼양식품", "ticker": "003230", "quantity": 1, "avg_buy_price": 0, "current_price": 1183000, "sector": "식품", "stage": "씨앗"},
]

INITIAL_TRANSACTIONS = [
    # SK하이닉스
    {"ticker": "000660", "stock_name": "SK하이닉스", "transaction_type": "매수", "quantity": 50, "price": 920000, "amount": 46000000, "memo": "초기매수"},
    {"ticker": "000660", "stock_name": "SK하이닉스", "transaction_type": "매수", "quantity": 26, "price": 944615, "amount": 24560000, "memo": "추가매수"},
    # 삼성전자
    {"ticker": "005930", "stock_name": "삼성전자", "transaction_type": "매수", "quantity": 300, "price": 190000, "amount": 57000000, "memo": "초기매수"},
    {"ticker": "005930", "stock_name": "삼성전자", "transaction_type": "매수", "quantity": 191, "price": 184921, "amount": 35300000, "memo": "추가매수"},
    # 삼성전기
    {"ticker": "009150", "stock_name": "삼성전기", "transaction_type": "매수", "quantity": 100, "price": 440000, "amount": 44000000, "memo": "초기매수"},
    {"ticker": "009150", "stock_name": "삼성전기", "transaction_type": "매수", "quantity": 76, "price": 440000, "amount": 33440000, "memo": "추가매수"},
    # 고려아연
    {"ticker": "010130", "stock_name": "고려아연", "transaction_type": "매수", "quantity": 22, "price": 1620000, "amount": 35640000, "memo": "초기매수"},
    # 하나머티리얼즈
    {"ticker": "166090", "stock_name": "하나머티리얼즈", "transaction_type": "매수", "quantity": 651, "price": 61500, "amount": 40036500, "memo": "초기매수"},
    # 에스앤에스텍
    {"ticker": "101490", "stock_name": "에스앤에스텍", "transaction_type": "매수", "quantity": 414, "price": 88000, "amount": 36432000, "memo": "초기매수"},
    # RFHIC
    {"ticker": "218410", "stock_name": "RFHIC", "transaction_type": "매수", "quantity": 920, "price": 72000, "amount": 66240000, "memo": "초기매수"},
    # 대한조선
    {"ticker": "439260", "stock_name": "대한조선", "transaction_type": "매수", "quantity": 480, "price": 97364, "amount": 46734720, "memo": "초기매수"},
    # HK이노엔
    {"ticker": "195940", "stock_name": "HK이노엔", "transaction_type": "매수", "quantity": 201, "price": 50000, "amount": 10050000, "memo": "초기매수"},
    # 한국피아이엠
    {"ticker": "448900", "stock_name": "한국피아이엠", "transaction_type": "매수", "quantity": 151, "price": 105000, "amount": 15855000, "memo": "초기매수"},
    # 티앤엘
    {"ticker": "340570", "stock_name": "티앤엘", "transaction_type": "매수", "quantity": 61, "price": 52400, "amount": 3196400, "memo": "초기매수"},
    # 삼성바이오로직스
    {"ticker": "207940", "stock_name": "삼성바이오로직스", "transaction_type": "매수", "quantity": 2, "price": 1606000, "amount": 3212000, "memo": "초기매수"},
    # S-Oil
    {"ticker": "010950", "stock_name": "S-Oil", "transaction_type": "매수", "quantity": 1, "price": 109700, "amount": 109700, "memo": "초기매수"},
    # 삼양식품
    {"ticker": "003230", "stock_name": "삼양식품", "transaction_type": "매수", "quantity": 1, "price": 1183000, "amount": 1183000, "memo": "초기매수"},
]


def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # 이미 데이터가 있으면 스킵
        existing = db.query(Stock).first()
        if existing:
            print("데이터가 이미 존재합니다. 초기화를 건너뜁니다.")
            return

        # 포트폴리오 현금 잔고 초기화
        portfolio = Portfolio(cash_balance=180277235)
        db.add(portfolio)

        # 종목 데이터 추가
        for stock_data in INITIAL_STOCKS:
            stock = Stock(**stock_data)
            db.add(stock)

        # 거래내역 추가
        for txn_data in INITIAL_TRANSACTIONS:
            txn = Transaction(**txn_data)
            db.add(txn)

        db.commit()
        print("초기 데이터 로드 완료!")

    except Exception as e:
        db.rollback()
        print(f"초기화 오류: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
