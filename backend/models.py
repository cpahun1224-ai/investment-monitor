from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Enum
from sqlalchemy.sql import func
from database import Base
import enum


class StageEnum(str, enum.Enum):
    seed = "씨앗"
    eco = "에코"
    pyramiding = "피라미딩"


class Stock(Base):
    __tablename__ = "stocks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    ticker = Column(String, nullable=False, unique=True)
    quantity = Column(Integer, default=0)
    avg_buy_price = Column(Float, default=0)
    current_price = Column(Float, default=0)
    sector = Column(String, default="")
    stage = Column(String, default="씨앗")
    target_price = Column(Float, default=0)
    stop_loss_price = Column(Float, default=0)
    memo = Column(Text, default="")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, nullable=False)
    stock_name = Column(String, nullable=False)
    transaction_type = Column(String, nullable=False)  # "매수" or "매도"
    quantity = Column(Integer, default=0)
    price = Column(Float, default=0)
    amount = Column(Float, default=0)
    memo = Column(Text, default="")
    created_at = Column(DateTime, server_default=func.now())


class Portfolio(Base):
    __tablename__ = "portfolio"

    id = Column(Integer, primary_key=True, index=True)
    cash_balance = Column(Float, default=0)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class StockAnalysis(Base):
    __tablename__ = "stock_analysis"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, nullable=False, unique=True, index=True)
    analysis_json = Column(Text, default="")
    news_json = Column(Text, default="")
    created_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
