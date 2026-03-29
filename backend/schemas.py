from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class StockBase(BaseModel):
    name: str
    ticker: str
    quantity: int = 0
    avg_buy_price: float = 0
    current_price: float = 0
    sector: str = ""
    stage: str = "씨앗"
    target_price: float = 0
    stop_loss_price: float = 0
    memo: str = ""


class StockCreate(StockBase):
    pass


class StockUpdate(BaseModel):
    quantity: Optional[int] = None
    avg_buy_price: Optional[float] = None
    current_price: Optional[float] = None
    sector: Optional[str] = None
    stage: Optional[str] = None
    target_price: Optional[float] = None
    stop_loss_price: Optional[float] = None
    memo: Optional[str] = None


class StockResponse(StockBase):
    id: int
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TransactionBase(BaseModel):
    ticker: str
    stock_name: str
    transaction_type: str
    quantity: int
    price: float
    amount: float
    memo: str = ""


class TransactionCreate(TransactionBase):
    pass


class TransactionResponse(TransactionBase):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PortfolioSummary(BaseModel):
    total_balance: float
    total_invested: float
    total_profit_loss: float
    profit_loss_rate: float
    cash_balance: float
    stock_value: float


class CashUpdate(BaseModel):
    cash_balance: float
