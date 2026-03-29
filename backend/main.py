from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta
import json
import models, schemas
from database import engine, get_db
from init_data import init_db
from price_fetcher import fetch_price, fetch_all_prices, is_market_open
from news_crawler import collect_stock_context
from gemini_analyzer import analyze_stock

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Investment Monitor API")

import os
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    init_db()


# ── 포트폴리오 요약 ──────────────────────────────────────────
@app.get("/api/portfolio/summary", response_model=schemas.PortfolioSummary)
def get_portfolio_summary(db: Session = Depends(get_db)):
    portfolio = db.query(models.Portfolio).first()
    cash = portfolio.cash_balance if portfolio else 0

    stocks = db.query(models.Stock).all()
    total_invested = sum(s.avg_buy_price * s.quantity for s in stocks)
    stock_value = sum(s.current_price * s.quantity for s in stocks)
    total_balance = cash + stock_value
    total_profit_loss = stock_value - total_invested
    profit_loss_rate = (total_profit_loss / total_invested * 100) if total_invested > 0 else 0

    return schemas.PortfolioSummary(
        total_balance=total_balance,
        total_invested=total_invested,
        total_profit_loss=total_profit_loss,
        profit_loss_rate=profit_loss_rate,
        cash_balance=cash,
        stock_value=stock_value,
    )


@app.put("/api/portfolio/cash")
def update_cash(data: schemas.CashUpdate, db: Session = Depends(get_db)):
    portfolio = db.query(models.Portfolio).first()
    if not portfolio:
        portfolio = models.Portfolio(cash_balance=data.cash_balance)
        db.add(portfolio)
    else:
        portfolio.cash_balance = data.cash_balance
    db.commit()
    return {"cash_balance": portfolio.cash_balance}


# ── 종목 관리 ─────────────────────────────────────────────────
@app.get("/api/stocks", response_model=List[schemas.StockResponse])
def get_stocks(db: Session = Depends(get_db)):
    return db.query(models.Stock).order_by(models.Stock.id).all()


@app.get("/api/stocks/{ticker}", response_model=schemas.StockResponse)
def get_stock(ticker: str, db: Session = Depends(get_db)):
    stock = db.query(models.Stock).filter(models.Stock.ticker == ticker).first()
    if not stock:
        raise HTTPException(status_code=404, detail="종목을 찾을 수 없습니다.")
    return stock


@app.post("/api/stocks", response_model=schemas.StockResponse)
def create_stock(stock: schemas.StockCreate, db: Session = Depends(get_db)):
    existing = db.query(models.Stock).filter(models.Stock.ticker == stock.ticker).first()
    if existing:
        raise HTTPException(status_code=400, detail="이미 존재하는 티커입니다.")
    db_stock = models.Stock(**stock.model_dump())
    db.add(db_stock)
    db.commit()
    db.refresh(db_stock)
    return db_stock


@app.put("/api/stocks/{ticker}", response_model=schemas.StockResponse)
def update_stock(ticker: str, stock_update: schemas.StockUpdate, db: Session = Depends(get_db)):
    stock = db.query(models.Stock).filter(models.Stock.ticker == ticker).first()
    if not stock:
        raise HTTPException(status_code=404, detail="종목을 찾을 수 없습니다.")
    update_data = stock_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(stock, key, value)
    db.commit()
    db.refresh(stock)
    return stock


@app.delete("/api/stocks/{ticker}")
def delete_stock(ticker: str, db: Session = Depends(get_db)):
    stock = db.query(models.Stock).filter(models.Stock.ticker == ticker).first()
    if not stock:
        raise HTTPException(status_code=404, detail="종목을 찾을 수 없습니다.")
    db.delete(stock)
    db.commit()
    return {"message": "삭제 완료"}


# ── 거래내역 ──────────────────────────────────────────────────
@app.get("/api/transactions", response_model=List[schemas.TransactionResponse])
def get_transactions(db: Session = Depends(get_db)):
    return db.query(models.Transaction).order_by(models.Transaction.created_at.desc()).limit(100).all()


@app.post("/api/transactions", response_model=schemas.TransactionResponse)
def create_transaction(txn: schemas.TransactionCreate, db: Session = Depends(get_db)):
    db_txn = models.Transaction(**txn.model_dump())
    db.add(db_txn)
    db.commit()
    db.refresh(db_txn)
    return db_txn


# ── 실시간 시세 ───────────────────────────────────────────────
@app.get("/api/prices/refresh")
def refresh_prices(db: Session = Depends(get_db)):
    """전체 종목 시세 갱신 (네이버 금융)"""
    stocks = db.query(models.Stock).all()
    tickers = [s.ticker for s in stocks]
    prices = fetch_all_prices(tickers)

    updated = []
    failed = []
    for stock in stocks:
        price = prices.get(stock.ticker)
        if price and price > 0:
            stock.current_price = float(price)
            updated.append({"ticker": stock.ticker, "name": stock.name, "price": price})
        else:
            failed.append(stock.ticker)

    db.commit()
    return {
        "updated": len(updated),
        "failed": failed,
        "prices": updated,
        "market_open": is_market_open(),
        "refreshed_at": datetime.now().isoformat(),
    }


@app.get("/api/prices/{ticker}")
def get_price(ticker: str, db: Session = Depends(get_db)):
    """단일 종목 시세 조회 및 DB 업데이트"""
    stock = db.query(models.Stock).filter(models.Stock.ticker == ticker).first()
    if not stock:
        raise HTTPException(status_code=404, detail="종목을 찾을 수 없습니다.")
    price = fetch_price(ticker)
    if price and price > 0:
        stock.current_price = float(price)
        db.commit()
    return {
        "ticker": ticker,
        "name": stock.name,
        "price": price or stock.current_price,
        "market_open": is_market_open(),
        "fetched_at": datetime.now().isoformat(),
    }


# ── 시그널 엔진 ───────────────────────────────────────────────
@app.get("/api/signals")
def get_signals(db: Session = Depends(get_db)):
    """종목별 GOOD/WATCH/RISK 시그널 계산"""
    portfolio = db.query(models.Portfolio).first()
    cash = portfolio.cash_balance if portfolio else 0
    stocks = db.query(models.Stock).all()
    total_value = sum(s.current_price * s.quantity for s in stocks) + cash

    results = []
    for s in stocks:
        if s.avg_buy_price <= 0:
            continue
        eval_val = s.current_price * s.quantity
        profit_rate = (s.current_price - s.avg_buy_price) / s.avg_buy_price * 100
        weight = eval_val / total_value * 100 if total_value > 0 else 0

        # 목표가 달성률
        target_rate = (s.current_price / s.target_price * 100) if s.target_price > 0 else None
        # 손절가까지 남은 %
        stop_gap = ((s.current_price - s.stop_loss_price) / s.current_price * 100) if s.stop_loss_price > 0 else None

        # 시그널 판정
        if profit_rate < -10 or (stop_gap is not None and stop_gap < 5):
            signal = "RISK"
        elif (-5 <= profit_rate <= 0) or (target_rate is not None and target_rate >= 90):
            signal = "WATCH"
        elif profit_rate > 0 and (target_rate is None or target_rate < 90):
            signal = "GOOD"
        else:
            signal = "WATCH"

        # 추가매수 여력
        add_buy_qty = int(cash / s.current_price) if s.current_price > 0 else 0

        results.append({
            "ticker": s.ticker,
            "name": s.name,
            "stage": s.stage,
            "sector": s.sector,
            "signal": signal,
            "current_price": s.current_price,
            "avg_buy_price": s.avg_buy_price,
            "profit_rate": round(profit_rate, 2),
            "profit_loss": round(eval_val - s.avg_buy_price * s.quantity),
            "eval_value": round(eval_val),
            "weight": round(weight, 2),
            "target_price": s.target_price,
            "target_rate": round(target_rate, 1) if target_rate else None,
            "stop_loss_price": s.stop_loss_price,
            "stop_gap": round(stop_gap, 1) if stop_gap is not None else None,
            "add_buy_qty": add_buy_qty,
            "memo": s.memo,
        })

    results.sort(key=lambda x: {"RISK": 0, "WATCH": 1, "GOOD": 2}[x["signal"]])
    return results


# ── 리밸런싱 가이드 ───────────────────────────────────────────
@app.get("/api/portfolio/rebalance")
def get_rebalance(db: Session = Depends(get_db)):
    """섹터별 현재비중 vs 목표비중 리밸런싱 가이드"""
    portfolio = db.query(models.Portfolio).first()
    cash = portfolio.cash_balance if portfolio else 0
    stocks = db.query(models.Stock).all()

    total_value = sum(s.current_price * s.quantity for s in stocks) + cash

    # 섹터별 집계
    sector_map = {}
    for s in stocks:
        val = s.current_price * s.quantity
        if s.sector not in sector_map:
            sector_map[s.sector] = {"value": 0, "stocks": []}
        sector_map[s.sector]["value"] += val
        sector_map[s.sector]["stocks"].append(s.name)

    result = []
    for sector, info in sorted(sector_map.items(), key=lambda x: -x[1]["value"]):
        cur_weight = info["value"] / total_value * 100 if total_value > 0 else 0
        result.append({
            "sector": sector,
            "value": round(info["value"]),
            "current_weight": round(cur_weight, 2),
            "stocks": info["stocks"],
        })

    result.append({
        "sector": "현금",
        "value": cash,
        "current_weight": round(cash / total_value * 100, 2) if total_value > 0 else 0,
        "stocks": [],
    })

    return {
        "total_value": round(total_value),
        "cash": cash,
        "sectors": result,
    }


# ── 매도 시나리오 ─────────────────────────────────────────────
@app.get("/api/stocks/{ticker}/sell-scenario")
def sell_scenario(ticker: str, db: Session = Depends(get_db)):
    """부분매도 / 전량매도 시나리오별 예상 수익"""
    stock = db.query(models.Stock).filter(models.Stock.ticker == ticker).first()
    if not stock:
        raise HTTPException(status_code=404, detail="종목을 찾을 수 없습니다.")

    portfolio = db.query(models.Portfolio).first()
    cash = portfolio.cash_balance if portfolio else 0
    all_stocks = db.query(models.Stock).all()
    total_value = sum(s.current_price * s.quantity for s in all_stocks) + cash

    scenarios = []
    for ratio in [25, 50, 75, 100]:
        qty = max(1, int(stock.quantity * ratio / 100))
        proceeds = qty * stock.current_price
        cost = qty * stock.avg_buy_price
        profit = proceeds - cost
        profit_rate = (profit / cost * 100) if cost > 0 else 0
        new_cash = cash + proceeds
        remaining_qty = stock.quantity - qty
        remaining_val = remaining_qty * stock.current_price
        new_total = total_value - proceeds + proceeds  # total unchanged
        scenarios.append({
            "ratio": ratio,
            "qty": qty,
            "proceeds": round(proceeds),
            "profit": round(profit),
            "profit_rate": round(profit_rate, 2),
            "new_cash": round(new_cash),
            "remaining_qty": remaining_qty,
            "remaining_value": round(remaining_val),
        })

    return {
        "ticker": ticker,
        "name": stock.name,
        "current_price": stock.current_price,
        "avg_buy_price": stock.avg_buy_price,
        "quantity": stock.quantity,
        "scenarios": scenarios,
    }


# ── AI 투자전략 분석 ──────────────────────────────────────────
@app.get("/api/analysis/{ticker}")
def get_analysis(ticker: str, db: Session = Depends(get_db)):
    """저장된 AI 분석 결과 조회 (캐시)"""
    rec = db.query(models.StockAnalysis).filter(models.StockAnalysis.ticker == ticker).first()
    if not rec:
        return {"cached": False, "analysis": None, "news": [], "created_at": None}
    return {
        "cached": True,
        "analysis": json.loads(rec.analysis_json) if rec.analysis_json else None,
        "news": json.loads(rec.news_json) if rec.news_json else [],
        "created_at": rec.created_at.isoformat() if rec.created_at else None,
    }


@app.post("/api/analysis/{ticker}")
def run_analysis(ticker: str, db: Session = Depends(get_db)):
    """단일 종목 AI 분석 실행 (24h 캐시)"""
    stock = db.query(models.Stock).filter(models.Stock.ticker == ticker).first()
    if not stock:
        raise HTTPException(status_code=404, detail="종목을 찾을 수 없습니다.")

    # 24h 캐시 확인
    rec = db.query(models.StockAnalysis).filter(models.StockAnalysis.ticker == ticker).first()
    if rec and rec.created_at:
        age = datetime.now() - rec.created_at
        if age < timedelta(hours=24):
            return {
                "cached": True,
                "analysis": json.loads(rec.analysis_json) if rec.analysis_json else None,
                "news": json.loads(rec.news_json) if rec.news_json else [],
                "created_at": rec.created_at.isoformat(),
            }

    # 컨텍스트 수집
    context = collect_stock_context(stock.name, stock.ticker)

    # Gemini 분석
    stock_dict = {
        "name": stock.name,
        "ticker": stock.ticker,
        "current_price": stock.current_price,
        "avg_buy_price": stock.avg_buy_price,
        "quantity": stock.quantity,
        "stage": stock.stage,
        "target_price": stock.target_price,
        "stop_loss_price": stock.stop_loss_price,
        "sector": stock.sector,
    }
    analysis = analyze_stock(stock_dict, context)

    # DB 저장
    if not rec:
        rec = models.StockAnalysis(ticker=ticker)
        db.add(rec)
    rec.analysis_json = json.dumps(analysis, ensure_ascii=False)
    rec.news_json = json.dumps(context.get("news", []), ensure_ascii=False)
    db.commit()
    db.refresh(rec)

    return {
        "cached": False,
        "analysis": analysis,
        "news": context.get("news", []),
        "created_at": rec.created_at.isoformat() if rec.created_at else None,
    }


@app.post("/api/analysis/batch")
def run_batch_analysis(db: Session = Depends(get_db)):
    """전체 종목 일괄 AI 분석"""
    stocks = db.query(models.Stock).all()
    results = []
    for stock in stocks:
        try:
            context = collect_stock_context(stock.name, stock.ticker)
            stock_dict = {
                "name": stock.name,
                "ticker": stock.ticker,
                "current_price": stock.current_price,
                "avg_buy_price": stock.avg_buy_price,
                "quantity": stock.quantity,
                "stage": stock.stage,
                "target_price": stock.target_price,
                "stop_loss_price": stock.stop_loss_price,
                "sector": stock.sector,
            }
            analysis = analyze_stock(stock_dict, context)

            rec = db.query(models.StockAnalysis).filter(models.StockAnalysis.ticker == stock.ticker).first()
            if not rec:
                rec = models.StockAnalysis(ticker=stock.ticker)
                db.add(rec)
            rec.analysis_json = json.dumps(analysis, ensure_ascii=False)
            rec.news_json = json.dumps(context.get("news", []), ensure_ascii=False)
            db.commit()
            results.append({"ticker": stock.ticker, "name": stock.name, "signal": analysis.get("signal"), "ok": True})
        except Exception as e:
            results.append({"ticker": stock.ticker, "name": stock.name, "ok": False, "error": str(e)})

    return {"total": len(stocks), "results": results}


# ── 섹터별 비중 ───────────────────────────────────────────────
@app.get("/api/portfolio/sector-weights")
def get_sector_weights(db: Session = Depends(get_db)):
    portfolio = db.query(models.Portfolio).first()
    cash = portfolio.cash_balance if portfolio else 0

    stocks = db.query(models.Stock).all()
    sector_map = {}
    for s in stocks:
        val = s.current_price * s.quantity
        sector_map[s.sector] = sector_map.get(s.sector, 0) + val

    total = sum(sector_map.values()) + cash
    result = []
    for sector, val in sorted(sector_map.items(), key=lambda x: -x[1]):
        result.append({"sector": sector, "value": val, "weight": round(val / total * 100, 2) if total > 0 else 0})

    if cash > 0:
        result.append({"sector": "현금", "value": cash, "weight": round(cash / total * 100, 2) if total > 0 else 0})

    return result
