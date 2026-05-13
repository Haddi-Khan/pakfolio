"""Pydantic request/response schemas."""

from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, field_validator, EmailStr
from models import TradeAction, TradeType, AssetType, CashTxType


# ── Auth ──────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    confirm_password: Optional[str] = None  # Yeh line add karein

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class ResendVerificationRequest(BaseModel):
    username_or_email: str



class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: str  # plain str to allow any email format


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class UserOut(BaseModel):
    id: int
    email: str
    avatar_url: Optional[str] = None
    is_active: bool
    created_at: datetime
    model_config = {"from_attributes": True}


# ── Portfolio ─────────────────────────────────────────────────────────────────

class PortfolioCreate(BaseModel):
    name: str
    description: Optional[str] = None
    initial_balance: float = 0.0

class PortfolioOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    is_default: bool
    created_at: datetime
    model_config = {"from_attributes": True}

class PortfolioUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


# ── Trade ─────────────────────────────────────────────────────────────────────

class TradeCreate(BaseModel):
    symbol: str
    name: Optional[str] = None
    action: TradeAction
    trade_type: TradeType = TradeType.LONG
    asset_type: AssetType = AssetType.STOCK
    price: float
    quantity: float
    deductions: float = 0.0
    trade_date: date
    notes: Optional[str] = None

    @field_validator("symbol")
    @classmethod
    def upper_symbol(cls, v: str) -> str:
        return v.strip().upper()


class TradeOut(BaseModel):
    id: int
    portfolio_id: int
    symbol: str
    name: Optional[str]
    action: TradeAction
    trade_type: TradeType
    asset_type: AssetType
    price: float
    quantity: float
    deductions: float
    trade_date: date
    notes: Optional[str]
    gross_value: float
    net_cost: float
    created_at: datetime
    model_config = {"from_attributes": True}

class TradeUpdate(BaseModel):
    price: Optional[float] = None
    quantity: Optional[float] = None
    deductions: Optional[float] = None
    trade_date: Optional[date] = None
    notes: Optional[str] = None


# ── Cash ──────────────────────────────────────────────────────────────────────

class CashTxCreate(BaseModel):
    tx_type: CashTxType
    amount: float
    tx_date: date
    description: Optional[str] = None


class CashTxOut(BaseModel):
    id: int
    portfolio_id: int
    tx_type: CashTxType
    amount: float
    tx_date: date
    description: Optional[str]
    created_at: datetime
    model_config = {"from_attributes": True}


# ── Holdings ──────────────────────────────────────────────────────────────────

class HoldingOut(BaseModel):
    symbol: str
    name: Optional[str]
    quantity: float
    avg_buy_price: float
    total_cost: float
    current_price: Optional[float]
    current_value: Optional[float]
    gain_loss: Optional[float]
    gain_loss_pct: Optional[float]
    day_change: Optional[float]
    day_change_pct: Optional[float]
    asset_type: AssetType
    sector: Optional[str] = None


# ── Portfolio Summary ─────────────────────────────────────────────────────────

class WinLossStats(BaseModel):
    wins: int = 0
    losses: int = 0
    total_trades: int = 0
    win_percentage: float = 0.0

class PortfolioSummary(BaseModel):
    portfolio_id: int
    portfolio_name: str
    total_deposited: float
    total_invested: float      # Net cost of open positions
    current_value: float       # Market value of open positions
    
    # P&L metrics
    total_unrealized_pnl: float # current_value - total_invested
    total_realized_pnl: float   # profit/loss from closed positions
    total_gain_loss: float      # total_unrealized_pnl + total_realized_pnl
    total_return_pct: float
    
    # Performance
    day_pnl: float             # Change in market value today
    day_pnl_pct: float
    dividend_income: float = 0.0
    
    cash_balance: float
    total_portfolio_value: float
    holdings_count: int
    win_loss: Optional[WinLossStats] = None


# ── Price ─────────────────────────────────────────────────────────────────────

class PriceOut(BaseModel):
    symbol: str
    price: Optional[float]
    change: Optional[float]
    change_pct: Optional[float]
    volume: Optional[int]
    open: Optional[float]
    high: Optional[float]
    low: Optional[float]
    prev_close: Optional[float]
    asset_type: Optional[str] = None
    aum: Optional[float] = None
    risk_profile: Optional[str] = None
    is_shariah: Optional[bool] = None
    category: Optional[str] = None


class SymbolSearchResult(BaseModel):
    symbol: str
    name: str
    sector: Optional[str] = None
    asset_type: Optional[str] = None  # stock, mutual_fund, etf
