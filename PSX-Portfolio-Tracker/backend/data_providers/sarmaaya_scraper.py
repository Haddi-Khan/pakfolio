"""Sarmaaya Mutual Fund Data Provider.

Replaces the old MUFAP HTML scraper (old.mufap.com.pk).

Fetches live NAV data from the Sarmaaya REST API:
    https://beta-restapi.sarmaaya.pk/api/mutual-funds

The API returns paginated JSON with 609+ funds.  We fetch all pages on first
request and cache results for CACHE_TTL_HOURS.  Results are indexed by fund
name (lowercase) so that CompositeProvider can look up a fund by its full name
(e.g. "Al Meezan Mutual Fund") using the existing symbol→name mapping in
MUTUAL_FUND_NAMES.

API Response structure (per item):
    {
        "fundId":        "uuid",
        "name":          "Al Meezan Mutual Fund",
        "symbol":        "",          # often empty — we use name-based lookup
        "riskProfile":   "Low",
        "nav":           43.99,
        "aum":           "123456789",
        "changePercent1d": 0.12,
        "isShariah":     true,
        "fundType":      "Mutual Fund"
    }

No authentication required.
"""

import logging
import random
import time
import threading
from datetime import datetime, timedelta
from typing import Optional, List, Dict

import httpx

from .base import BaseDataProvider, QuoteData, OHLCVPoint, SymbolInfo

logger = logging.getLogger(__name__)

BASE_URL = "https://beta-restapi.sarmaaya.pk/api/mutual-funds"
PAGE_SIZE = 1000         # Get all funds in one page if possible to avoid pagination 401s
CACHE_TTL_HOURS = 12

# Global lock to prevent "Thundering Herd" when multiple threads refresh cache
_sarmaaya_lock = threading.Lock()

# Rotate User-Agents to look more natural
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
]

TIMEOUT = 30


class SarmaayaScraper(BaseDataProvider):
    """Fetches mutual fund NAVs from Sarmaaya REST API, cached for CACHE_TTL_HOURS."""

    def __init__(self):
        self._client = httpx.Client(
            headers={"Accept": "application/json"}, 
            timeout=TIMEOUT, 
            follow_redirects=True
        )
        # lowercase fund name → QuoteData
        self._name_cache: Dict[str, QuoteData] = {}
        # UPPERCASE symbol → QuoteData (only for funds with a non-empty symbol field)
        self._symbol_cache: Dict[str, QuoteData] = {}
        # UPPERCASE symbol → fundId (UUID)
        self._fund_ids: Dict[str, str] = {}
        self._symbols: List[SymbolInfo] = []
        self._last_fetch: Optional[datetime] = None

    # ── Public interface ──────────────────────────────────────────────────────

    def get_quote(self, symbol: str) -> QuoteData:
        """Look up a fund by its ticker symbol (e.g. AMMF, ALHAA, MIF)."""
        self._ensure_cache()
        upper = symbol.upper().strip()
        return self._symbol_cache.get(upper, QuoteData(symbol=upper))

    def get_all_mf_symbols(self) -> set:
        """Return the set of all mutual fund symbols known from Sarmaaya API."""
        self._ensure_cache()
        return set(self._symbol_cache.keys())

    def get_quotes_bulk(self, symbols: List[str]) -> Dict[str, QuoteData]:
        self._ensure_cache()
        return {
            s.upper(): self._symbol_cache.get(s.upper().strip(), QuoteData(symbol=s.upper()))
            for s in symbols
        }

    def get_historical(self, symbol: str, from_date: str, to_date: str) -> List[OHLCVPoint]:
        self._ensure_cache()
        upper = symbol.upper().strip()
        fid = self._fund_ids.get(upper)
        if not fid:
            return []

        # Sarmaaya nav-history endpoint uses /api/mutual-funds/nav-history/{fid}?days={days}
        days = "infinity" # Use infinity to get full history

        max_retries = 3
        for attempt in range(max_retries):
            try:
                headers = {"User-Agent": random.choice(USER_AGENTS)}
                url = f"https://beta-restapi.sarmaaya.pk/api/mutual-funds/nav-history/{fid}"
                resp = self._client.get(url, params={"days": days}, headers=headers)
                if resp.status_code == 429:
                    wait = (attempt + 1) * 1.5
                    logger.warning(f"Sarmaaya MF 429. Retrying in {wait}s...")
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                data = resp.json().get("response", [])
                
                points = []
                for item in data:
                    dt_str = item.get("date", "").split("T")[0]
                    nav = float(item.get("nav") or 0)
                    if not dt_str or nav <= 0:
                        continue
                    points.append(OHLCVPoint(
                        date=dt_str,
                        open=nav, high=nav, low=nav, close=nav, volume=0
                    ))
                return sorted(points, key=lambda p: p.date)
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.warning(f"Failed to fetch MF history for {symbol} after {max_retries} attempts: {e}")
                    return []
                time.sleep(1)
        return []

    def search_symbols(self, query: str) -> List[SymbolInfo]:
        self._ensure_cache()
        q = query.lower()
        return [s for s in self._symbols if q in s.symbol.lower() or q in s.name.lower()][:20]

    def get_all_symbols(self) -> List[SymbolInfo]:
        self._ensure_cache()
        return list(self._symbols)

    def get_nav_by_name(self, name: str) -> Optional[QuoteData]:
        """
        Look up the latest NAV by full fund name (case-insensitive, partial match).
        e.g. get_nav_by_name("Al Meezan Mutual Fund") → QuoteData(price=43.99, ...)
        """
        self._ensure_cache()
        name_lower = name.lower().strip()

        # Exact match first
        if name_lower in self._name_cache:
            return self._name_cache[name_lower]

        # Partial / substring match
        for cached_name, qd in self._name_cache.items():
            if name_lower in cached_name or cached_name in name_lower:
                return qd

        return None

    # ── Cache management ──────────────────────────────────────────────────────

    def _ensure_cache(self):
        now = datetime.utcnow()
        # 1. Quick check without lock (most common case)
        if self._last_fetch and (now - self._last_fetch) < timedelta(hours=CACHE_TTL_HOURS):
            return
        
        # If we have stale data, refresh in background to avoid blocking the user
        if self._last_fetch and self._name_cache:
            # Only trigger background refresh once
            with _sarmaaya_lock:
                if (now - self._last_fetch) < timedelta(hours=CACHE_TTL_HOURS):
                    return
                # Update last_fetch immediately to "lock" the background task
                self._last_fetch = now
                threading.Thread(target=self._background_refresh, daemon=True).start()
            return

        # 2. Lock and check again (double-checked locking pattern) for initial load
        with _sarmaaya_lock:
            # Re-check because another thread might have finished while we waited for lock
            if self._last_fetch and (datetime.utcnow() - self._last_fetch) < timedelta(hours=CACHE_TTL_HOURS):
                return

            try:
                self._fetch_all_navs()
                self._last_fetch = datetime.utcnow()
                logger.info(f"Sarmaaya cache refreshed: {len(self._name_cache)} fund NAVs loaded")
            except Exception as e:
                logger.warning(f"Sarmaaya fetch failed: {e}")
                # Cooldown logic remains
                if self._last_fetch:
                    self._last_fetch = datetime.utcnow() - timedelta(hours=CACHE_TTL_HOURS - 1)
                else:
                    self._last_fetch = datetime.utcnow() - timedelta(hours=CACHE_TTL_HOURS) + timedelta(minutes=5)

    def _background_refresh(self):
        """Refreshes the cache in a background thread."""
        try:
            logger.info("Sarmaaya background cache refresh started...")
            self._fetch_all_navs()
            logger.info(f"Sarmaaya background cache refreshed: {len(self._name_cache)} fund NAVs loaded")
        except Exception as e:
            logger.warning(f"Sarmaaya background fetch failed: {e}")

    def _fetch_all_navs(self):
        """Paginate through the Sarmaaya API and build the name/symbol → QuoteData caches."""
        name_cache: Dict[str, QuoteData] = {}
        symbol_cache: Dict[str, QuoteData] = {}
        fund_ids: Dict[str, str] = {}
        symbols: List[SymbolInfo] = []

        page = 1
        while True:
            body = None
            # Reduced delay for smoother performance since we have locking now
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    headers = {"User-Agent": random.choice(USER_AGENTS)}
                    resp = self._client.get(
                        BASE_URL,
                        params={"page": page, "limit": PAGE_SIZE},
                        headers=headers
                    )
                    if resp.status_code == 429:
                        wait = (attempt + 1) * 2 # Reduced wait
                        logger.warning(f"Sarmaaya MF Listing 429. Waiting {wait}s...")
                        time.sleep(wait)
                        continue
                    if resp.status_code == 401:
                        logger.warning(f"Sarmaaya MF API 401 Unauthorized (likely requires API key). Skipping.")
                        body = {} # Stop pagination for now but keep results
                        break
                    resp.raise_for_status()
                    body = resp.json()
                    break
                except Exception as e:
                    if attempt == max_retries - 1:
                        logger.warning(f"Sarmaaya API page {page} fetch failed: {e}")
                        body = {}
                        break
                    time.sleep(1)

            if not body:
                break

            if not body.get("success"):
                logger.warning(f"Sarmaaya API returned success=false on page {page}")
                break

            response_data = body.get("response", {})
            items = response_data.get("data", [])

            for item in items:
                raw_name: str = item.get("name", "").strip()
                raw_symbol: str = (item.get("symbol") or "").strip()
                nav = item.get("nav")
                change_pct = item.get("changePercent1d")

                if not raw_name or nav is None:
                    continue

                try:
                    price = float(nav)
                except (TypeError, ValueError):
                    continue

                if price <= 0:
                    continue

                # Calculate prev_close and absolute change from daily % change
                prev_close: Optional[float] = None
                if change_pct is not None:
                    try:
                        pct = float(change_pct)
                        denom = 1.0 + pct / 100.0
                        if denom != 0:
                            prev_close = price / denom
                    except (TypeError, ValueError, ZeroDivisionError):
                        prev_close = None

                change: Optional[float] = (price - prev_close) if prev_close is not None else None
                change_pct_val: Optional[float] = float(change_pct) if change_pct is not None else None

                qd = QuoteData(
                    symbol=raw_symbol if raw_symbol else raw_name,
                    price=price,
                    prev_close=prev_close,
                    change=change,
                    change_pct=change_pct_val,
                    asset_type="mutual_fund",
                    aum=_to_float(item.get("aum")),
                    risk_profile=item.get("riskProfile"),
                    is_shariah=item.get("isShariah"),
                    category=item.get("fundType"),
                )

                # Always index by lowercase name (for get_nav_by_name fallback)
                name_cache[raw_name.lower()] = qd

                # Also index by symbol (used for direct ticker lookup)
                if raw_symbol:
                    sym_key = raw_symbol.upper().strip()
                    # Store first occurrence when multiple sub-classes share a symbol
                    if sym_key not in symbol_cache:
                        symbol_cache[sym_key] = QuoteData(
                            symbol=sym_key,
                            price=price,
                            prev_close=prev_close,
                            change=change,
                            change_pct=change_pct_val,
                            asset_type="mutual_fund",
                            aum=_to_float(item.get("aum")),
                            risk_profile=item.get("riskProfile"),
                            is_shariah=item.get("isShariah"),
                            category=item.get("fundType"),
                        )

                # Use ticker symbol as identifier in the searchable list when available
                fid = item.get("fundId")
                fund_ids[raw_name.upper()] = fid
                if raw_symbol:
                    fund_ids[raw_symbol.upper()] = fid

                symbols.append(SymbolInfo(
                    symbol=raw_symbol if raw_symbol else raw_name,
                    name=raw_name,
                    asset_type="mutual_fund",
                ))

            # Check if there are more pages
            next_page = response_data.get("next")
            if next_page is None:
                break
            page = next_page

        self._name_cache = name_cache
        self._symbol_cache = symbol_cache
        self._fund_ids = fund_ids
        self._symbols = symbols

# ── helpers ───────────────────────────────────────────────────────────────────

def _to_float(val) -> Optional[float]:
    try:
        if val is None: return None
        return float(str(val).replace(",", ""))
    except (ValueError, TypeError):
        return None
