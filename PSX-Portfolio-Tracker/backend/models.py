"""SQLAlchemy ORM models."""

from datetime import datetime, date
from sqlalchemy import (
    Column, Integer, String, Float, Date, DateTime,
    Enum as SAEnum, Text, ForeignKey, Boolean, Numeric, Index
)
from sqlalchemy.orm import DeclarativeBase, relationship
import enum


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=True)  # Nullable for social users
    avatar_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Auth verification and reset
    is_verified = Column(Boolean, default=False)
    verification_token = Column(String(255), nullable=True)
    last_verification_sent_at = Column(DateTime(timezone=True), nullable=True)
    verification_sent_count = Column(Integer, default=0)
    reset_token = Column(String(255), nullable=True)
    reset_token_expiry = Column(DateTime(timezone=True), nullable=True)

    portfolios = relationship("Portfolio", back_populates="user", cascade="all, delete-orphan")
    reset_tokens = relationship("PasswordResetToken", back_populates="user", cascade="all, delete-orphan")
    social_accounts = relationship("SocialAccount", back_populates="user", cascade="all, delete-orphan")


class SocialAccount(Base):
    __tablename__ = "social_accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    provider = Column(String(20), nullable=False)  # google, facebook, apple
    provider_user_id = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="social_accounts")

    __table_args__ = (
        Index("idx_provider_user", "provider", "provider_user_id", unique=True),
    )


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    # Store SHA-256 hash of the token, never the raw value
    token_hash = Column(String(64), nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="reset_tokens")


class TradeAction(str, enum.Enum):
    BUY = "BUY"
    SELL = "SELL"


class TradeType(str, enum.Enum):
    LONG = "LONG"
    SHORT = "SHORT"


class AssetType(str, enum.Enum):
    STOCK = "STOCK"
    MUTUAL_FUND = "MUTUAL_FUND"
    ETF = "ETF"
    INDEX = "INDEX"

    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            for member in cls:
                if member.value.upper() == value.upper():
                    return member
        return super()._missing_(value)


class CashTxType(str, enum.Enum):
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"


class Portfolio(Base):
    __tablename__ = "portfolios"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="portfolios")
    trades = relationship("Trade", back_populates="portfolio", cascade="all, delete-orphan")
    cash_transactions = relationship("CashTransaction", back_populates="portfolio", cascade="all, delete-orphan")


class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False, index=True)
    symbol = Column(String(100), nullable=False, index=True)
    name = Column(String(200))
    action = Column(SAEnum(TradeAction), nullable=False)
    trade_type = Column(SAEnum(TradeType), default=TradeType.LONG)
    asset_type = Column(SAEnum(AssetType), default=AssetType.STOCK)
    price = Column(Numeric(16, 4), nullable=False)
    quantity = Column(Numeric(16, 4), nullable=False)
    deductions = Column(Numeric(16, 4), default=0.0)
    trade_date = Column(Date, nullable=False)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    portfolio = relationship("Portfolio", back_populates="trades")

    @property
    def gross_value(self) -> float:
        return self.price * self.quantity

    @property
    def net_cost(self) -> float:
        if self.action == TradeAction.BUY:
            return self.gross_value + self.deductions
        return self.gross_value - self.deductions


class CashTransaction(Base):
    __tablename__ = "cash_transactions"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False, index=True)
    tx_type = Column(SAEnum(CashTxType), nullable=False)
    amount = Column(Numeric(16, 4), nullable=False)
    tx_date = Column(Date, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    portfolio = relationship("Portfolio", back_populates="cash_transactions")


class HistoricalPrice(Base):
    __tablename__ = "historical_prices"

    symbol = Column(String(100), primary_key=True)
    date = Column(Date, primary_key=True)
    price = Column(Numeric(16, 4), nullable=False)
    asset_type = Column(SAEnum(AssetType), nullable=False)

    __table_args__ = (
        Index("idx_symbol_date", "symbol", "date"),
    )


class LivePrice(Base):
    __tablename__ = "live_prices"

    symbol = Column(String(100), primary_key=True)
    price = Column(Numeric(16, 4), nullable=False)
    change = Column(Numeric(16, 4))
    change_pct = Column(Numeric(16, 4))
    open = Column(Numeric(16, 4))
    high = Column(Numeric(16, 4))
    low = Column(Numeric(16, 4))
    prev_close = Column(Numeric(16, 4))
    dividend_yield = Column(Numeric(16, 4))
    dividend_payout = Column(Numeric(16, 4))
    volume = Column(Numeric(16, 4))
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class GlobalSymbol(Base):
    __tablename__ = "global_symbols"

    symbol = Column(String(100), primary_key=True, index=True)
    name = Column(String(200), nullable=True, index=True)
    sector = Column(String(200), nullable=True, index=True)
    asset_type = Column(SAEnum(AssetType), default=AssetType.STOCK, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class HistoryPSX(Base):
    __tablename__ = "history_psx"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(100), index=True, nullable=False)
    symbol_name = Column(String(255), nullable=True)
    date = Column(Date, index=True, nullable=False)
    open = Column(Numeric(16, 4))
    high = Column(Numeric(16, 4))
    low = Column(Numeric(16, 4))
    close = Column(Numeric(16, 4))
    volume = Column(Numeric(20, 4))

    # Technical Indicators
    sma_50 = Column(Numeric(16, 4))
    sma_200 = Column(Numeric(16, 4))
    sma_20 = Column(Numeric(16, 4), index=True)
    std_20 = Column(Numeric(16, 4))
    bbl_20_2_0 = Column(Numeric(16, 4))
    bbu_20_2_0 = Column(Numeric(16, 4))
    rsi_14 = Column(Numeric(16, 4))

    __table_args__ = (
        Index("idx_history_psx_symbol_date", "symbol", "date", unique=True),
    )
