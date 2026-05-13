"""Abstract base class for all data providers.

To add a new provider (e.g. PSXTerminal, CapitalStake, EODHD):
1. Create a new file in this directory (e.g. psxterminal.py)
2. Subclass BaseDataProvider and implement all abstract methods
3. In __init__.py swap: active_provider = YourNewProvider()
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict
from dataclasses import dataclass


@dataclass
class QuoteData:
    symbol: str
    price: Optional[float] = None
    change: Optional[float] = None
    change_pct: Optional[float] = None
    volume: Optional[int] = None
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    prev_close: Optional[float] = None
    name: Optional[str] = None
    isin: Optional[str] = None
    asset_type: Optional[str] = None  # stock, mutual_fund, etf
    aum: Optional[float] = None
    risk_profile: Optional[str] = None
    is_shariah: Optional[bool] = None
    category: Optional[str] = None
    sector_name: Optional[str] = None


@dataclass
class OHLCVPoint:
    date: str        # ISO format YYYY-MM-DD
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass
class SymbolInfo:
    symbol: str
    name: str
    sector: Optional[str] = None
    asset_type: Optional[str] = None  # stock, mutual_fund, etf


class BaseDataProvider(ABC):

    @abstractmethod
    def get_quote(self, symbol: str) -> QuoteData:
        """Fetch current quote for a single symbol."""
        ...

    @abstractmethod
    def get_quotes_bulk(self, symbols: List[str]) -> Dict[str, QuoteData]:
        """Fetch current quotes for multiple symbols. Returns dict[symbol -> QuoteData]."""
        ...

    @abstractmethod
    def get_historical(self, symbol: str, from_date: str, to_date: str) -> List[OHLCVPoint]:
        """Fetch OHLCV history between ISO date strings."""
        ...

    @abstractmethod
    def search_symbols(self, query: str) -> List[SymbolInfo]:
        """Search for symbols by name or ticker."""
        ...

    @abstractmethod
    def get_all_symbols(self) -> List[SymbolInfo]:
        """Return all available symbols from this provider."""
        ...
