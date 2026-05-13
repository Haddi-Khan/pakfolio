"""Composite data provider.

Routes requests by asset type:
  - stock / etf   → PSXScraper     (dps.psx.com.pk)
  - mutual_fund   → SarmaayaScraper (beta-restapi.sarmaaya.pk)

Mutual fund detection works in two ways:
  1. Dynamic:  Any symbol in the Sarmaaya API with a non-empty 'symbol' field
               is automatically recognised as a mutual fund at runtime.
               This covers 400+ funds out of the 609 on sarmaaya.pk — no code
               changes needed when new funds are listed.
  2. Manual:   MUTUAL_FUND_NAMES below — a tiny fallback for funds whose
               Sarmaaya entry has an empty symbol field.  Add funds here only
               if they don't appear with a symbol in Sarmaaya.
"""

from typing import Optional, List, Dict

from .base import BaseDataProvider, QuoteData, OHLCVPoint, SymbolInfo
from .psx_scraper import PSXScraper
from .sarmaaya_scraper import SarmaayaScraper
from .sarmaaya_provider import SarmaayaProvider


# Fallback mapping: ticker → full fund name.
# Only needed for funds whose Sarmaaya entry has an EMPTY 'symbol' field.
# The vast majority of funds are detected automatically from Sarmaaya's API.
# To add a new mutual fund: just use it in a trade — if it has a symbol in
# Sarmaaya it will resolve automatically. Only add here if it doesn't.
MUTUAL_FUND_NAMES: Dict[str, str] = {
    # Examples — uncomment / add only if the fund has no symbol in Sarmaaya:
    # "MYFUND": "My Full Fund Name",
}

# Manual fallback symbols (mirrors keys of MUTUAL_FUND_NAMES)
MUTUAL_FUND_SYMBOLS = set(MUTUAL_FUND_NAMES.keys())


class CompositeProvider(BaseDataProvider):

    def __init__(self):
        self._psx = PSXScraper()
        self._mufap = SarmaayaScraper()
        self._sarmaaya = SarmaayaProvider()

    def register_mutual_fund(self, symbol: str, full_name: str):
        """Register a mutual fund symbol → MUFAP name mapping at runtime."""
        MUTUAL_FUND_SYMBOLS.add(symbol.upper())
        MUTUAL_FUND_NAMES[symbol.upper()] = full_name

    def _is_mf(self, symbol: str) -> bool:
        upper = symbol.upper()
        # 1. Is it in our manual fallback set?
        if upper in MUTUAL_FUND_SYMBOLS:
            return True
        # 2. Does Sarmaaya know this as a mutual fund symbol? (covers all 400+ funds)
        return upper in self._mufap.get_all_mf_symbols()

    # ── Quote ─────────────────────────────────────────────────────────────────

    def get_quote(self, symbol: str) -> QuoteData:
        upper = symbol.upper()
        if self._is_mf(upper):
            return self._get_mf_quote(upper)
        
        # 1. Try PSX Scraper first (more reliable, no auth needed)
        q = self._psx.get_quote(upper)
        
        # 2. Fallback to Sarmaaya only if PSX is missing critical data
        if q.price is None or q.change is None or q.open is None:
            s_q = self._sarmaaya.get_quote(upper)
            
            if q.price is None:
                q.price = s_q.price
                q.prev_close = s_q.prev_close
            
            if q.change is None or (q.change == 0 and s_q.change != 0):
                q.change = s_q.change
                q.change_pct = s_q.change_pct
            
            if q.open is None or q.open == 0:
                q.open = s_q.open
            
            if q.high is None or q.high == 0:
                q.high = s_q.high
            
            if q.low is None or q.low == 0:
                q.low = s_q.low
            
            if q.volume is None or q.volume == 0:
                q.volume = s_q.volume

            # Final safety: If we have price and prev_close but no change, calculate it
            if q.change is None and q.price is not None and q.prev_close:
                q.change = q.price - q.prev_close
                if q.prev_close != 0:
                    q.change_pct = (q.change / q.prev_close) * 100
        
        return q

    def get_quotes_bulk(self, symbols: List[str]) -> Dict[str, QuoteData]:
        stock_syms = [s for s in symbols if not self._is_mf(s)]
        mf_syms    = [s for s in symbols if self._is_mf(s)]

        result: Dict[str, QuoteData] = {}

        if stock_syms:
            # 1. Try PSX Scraper first
            psx_quotes = self._psx.get_quotes_bulk(stock_syms)
            missing_stock_syms = []
            
            for sym in stock_syms:
                q = psx_quotes.get(sym.upper())
                if not q or q.price is None:
                    missing_stock_syms.append(sym)
                if q:
                    result[sym.upper()] = q
                else:
                    result[sym.upper()] = QuoteData(symbol=sym.upper())
            
            # 2. Fallback to Sarmaaya for missing stocks
            if missing_stock_syms:
                sarmaaya_quotes = self._sarmaaya.get_quotes_bulk(missing_stock_syms)
                for sym, s_q in sarmaaya_quotes.items():
                    if sym in result and s_q.price is not None:
                        q = result[sym]
                        if q.price is None:
                            result[sym] = s_q
                        else:
                            # Fill missing fields from Sarmaaya
                            if q.open is None: q.open = s_q.open
                            if q.high is None: q.high = s_q.high
                            if q.low is None: q.low = s_q.low
                            if not q.volume: q.volume = s_q.volume

        if mf_syms:
            # Use self._mufap (SarmaayaScraper) bulk fetch which is efficient
            mf_quotes = self._mufap.get_quotes_bulk(mf_syms)
            for sym, q in mf_quotes.items():
                # If symbol-based lookup failed, try name-based fallback (for manual list)
                if q.price is None:
                    q = self._get_mf_quote(sym)
                result[sym.upper()] = q

        return result

    def _get_mf_quote(self, symbol: str) -> QuoteData:
        upper = symbol.upper()

        # 1. Direct symbol lookup via Sarmaaya (works for any fund with a symbol)
        q = self._mufap.get_quote(upper)
        if q.price:
            return q

        # 2. Name-based fallback (for funds in the manual MUTUAL_FUND_NAMES dict)
        full_name = MUTUAL_FUND_NAMES.get(upper)
        if full_name:
            q = self._mufap.get_nav_by_name(full_name)
            if q:
                return QuoteData(
                    symbol=upper,
                    price=q.price,
                    change=q.change,
                    change_pct=q.change_pct,
                    prev_close=q.prev_close,
                )

        return QuoteData(symbol=upper)

    # ── Historical ────────────────────────────────────────────────────────────

    def get_historical(self, symbol: str, from_date: str, to_date: str) -> List[OHLCVPoint]:
        if self._is_mf(symbol):
            return self._mufap.get_historical(symbol, from_date, to_date)
        
        # 1. Try PSX Scraper first
        points = self._psx.get_historical(symbol, from_date, to_date)
        if points:
            return points
        
        # 2. Fallback to Sarmaaya
        return self._sarmaaya.get_historical(symbol, from_date, to_date)

    # ── Symbol Search ─────────────────────────────────────────────────────────

    def search_symbols(self, query: str) -> List[SymbolInfo]:
        psx_results = self._psx.search_symbols(query)
        mf_results  = self._mufap.search_symbols(query)
        seen = {r.symbol for r in psx_results}
        combined = psx_results + [r for r in mf_results if r.symbol not in seen]
        return combined[:20]

    def get_all_symbols(self) -> List[SymbolInfo]:
        psx_syms = self._psx.get_all_symbols()
        mf_syms  = self._mufap.get_all_symbols()
        seen = {s.symbol for s in psx_syms}
        return psx_syms + [s for s in mf_syms if s.symbol not in seen]
