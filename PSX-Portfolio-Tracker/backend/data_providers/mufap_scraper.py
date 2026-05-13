"""MUFAP NAV Scraper — parses old.mufap.com.pk HTML tables.

Fetches latest NAVs for mutual funds once every CACHE_TTL_HOURS and caches in memory.

Table structure (open-end, tab=01):
  Fund Name | Category | Inception Date | Class | Type | Offer | Repurchase | NAV | Validity Date | ...

The table includes ALL historical rows. We take the latest Validity Date per fund.
We fetch per-AMC to limit response size instead of fetching all funds at once.

AMC IDs for our funds:
  A024 — Al Meezan Investment Management Limited
  A015 — HBL Asset Management Limited (Alhamra funds)
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict

import httpx

from .base import BaseDataProvider, QuoteData, OHLCVPoint, SymbolInfo

logger = logging.getLogger(__name__)

BASE_URL = "https://old.mufap.com.pk/nav-report.php"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; PSXTracker/1.0)",
    "Accept": "text/html,application/xhtml+xml",
}
TIMEOUT = 30
CACHE_TTL_HOURS = 12

# MUFAP AMC IDs for the fund families we track.
# Fetching per-AMC keeps response size manageable (~few KB vs 600MB for all).
AMC_IDS = [
    "A024",  # Al Meezan Investment Management Limited
    "A015",  # HBL Asset Management Limited (Alhamra funds)
]


class MUFAPScraper(BaseDataProvider):
    """Scrapes MUFAP for latest mutual fund NAV prices, cached for CACHE_TTL_HOURS."""

    def __init__(self):
        self._client = httpx.Client(headers=HEADERS, timeout=TIMEOUT, follow_redirects=True)
        # name_index: lowercase fund name → QuoteData
        self._name_cache: Dict[str, QuoteData] = {}
        self._symbols: List[SymbolInfo] = []
        self._last_fetch: Optional[datetime] = None
        self._amc_ids: List[str] = list(AMC_IDS)

    # ── Public interface ──────────────────────────────────────────────────────

    def get_quote(self, symbol: str) -> QuoteData:
        # MUFAPScraper doesn't know about short symbols — use get_nav_by_name()
        return QuoteData(symbol=symbol.upper())

    def get_quotes_bulk(self, symbols: List[str]) -> Dict[str, QuoteData]:
        return {s.upper(): QuoteData(symbol=s.upper()) for s in symbols}

    def get_historical(self, symbol: str, from_date: str, to_date: str) -> List[OHLCVPoint]:
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
        Look up latest NAV by full fund name (case-insensitive partial match).
        e.g. get_nav_by_name("Al Meezan Mutual Fund") → QuoteData(price=43.99...)
        """
        self._ensure_cache()
        name_lower = name.lower().strip()
        # Exact match
        if name_lower in self._name_cache:
            return self._name_cache[name_lower]
        # Partial match — find best overlap
        for cached_name, qd in self._name_cache.items():
            if name_lower in cached_name or cached_name in name_lower:
                return qd
        return None

    # ── Cache management ──────────────────────────────────────────────────────

    def _ensure_cache(self):
        now = datetime.utcnow()
        if self._last_fetch and (now - self._last_fetch) < timedelta(hours=CACHE_TTL_HOURS):
            return
        try:
            self._fetch_all_navs()
            self._last_fetch = now
            logger.info(f"MUFAP cache refreshed: {len(self._name_cache)} fund NAVs loaded")
        except Exception as e:
            logger.warning(f"MUFAP fetch failed: {e}")
            if not self._last_fetch:
                self._last_fetch = now  # prevent retry storm

    def _fetch_all_navs(self):
        """Fetch NAVs per registered AMC and merge results."""
        merged_cache: Dict[str, QuoteData] = {}
        merged_symbols: List[SymbolInfo] = []
        for amc_id in self._amc_ids:
            try:
                resp = self._client.get(
                    BASE_URL,
                    params={"tab": "01", "amc": amc_id, "submitted": "true"},
                )
                resp.raise_for_status()
                cache, symbols = self._parse_nav_html(resp.text)
                merged_cache.update(cache)
                merged_symbols.extend(symbols)
            except Exception as e:
                logger.warning(f"MUFAP fetch failed for AMC {amc_id}: {e}")
        self._name_cache = merged_cache
        self._symbols = merged_symbols

    def register_amc(self, amc_id: str):
        """Add an AMC ID to fetch on next cache refresh."""
        if amc_id not in self._amc_ids:
            self._amc_ids.append(amc_id)

    def _parse_nav_html(self, html: str) -> tuple:
        """
        Parse MUFAP NAV table. Takes the most recent row per fund name.
        Returns (name_cache dict, symbols list).

        Columns: Fund Name(0) | Category(1) | Inception(2) | Class(3) | Type(4)
                 Offer(5) | Repurchase(6) | NAV(7) | Validity Date(8) | ...
        """
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            logger.error("beautifulsoup4 not installed. Run: pip install beautifulsoup4")
            return {}, []

        soup = BeautifulSoup(html, "lxml")
        name_cache: Dict[str, QuoteData] = {}
        latest_date: Dict[str, str] = {}

        for table in soup.find_all("table"):
            rows = table.find_all("tr")
            if len(rows) < 5:
                continue

            header_cells = [c.get_text(strip=True).lower() for c in rows[0].find_all(["th", "td"])]
            if "fund name" not in header_cells and "offer" not in header_cells:
                continue

            name_col  = _col(header_cells, ["fund name", "name"])
            nav_col   = _col(header_cells, ["nav"])
            offer_col = _col(header_cells, ["offer"])
            date_col  = _col(header_cells, ["validity date", "validity", "date"])
            repr_col  = _col(header_cells, ["repurchase"])
            price_col = nav_col if nav_col is not None else offer_col

            if name_col is None or price_col is None:
                continue

            for row in rows[1:]:
                cells = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
                if len(cells) <= price_col:
                    continue

                fund_name = cells[name_col].strip()
                if not fund_name or fund_name.lower() in ("fund name", ""):
                    continue
                if sum(1 for c in cells if c.strip()) <= 2:
                    continue  # AMC header row

                price = _to_float(cells[price_col])
                if price is None or price <= 0:
                    continue

                validity_str = cells[date_col].strip() if date_col is not None and len(cells) > date_col else ""
                validity = _parse_mufap_date(validity_str)
                name_key = fund_name.lower()

                if name_key in latest_date and validity and validity <= latest_date[name_key]:
                    continue
                latest_date[name_key] = validity or ""

                prev = _to_float(cells[repr_col]) if repr_col and len(cells) > repr_col else None
                name_cache[name_key] = QuoteData(symbol=fund_name, price=price, prev_close=prev)

            if name_cache:
                break

        symbols = [SymbolInfo(symbol=qd.symbol, name=qd.symbol) for qd in name_cache.values()]
        return name_cache, symbols


# ── Helpers ───────────────────────────────────────────────────────────────────

def _col(headers: list, candidates: list) -> Optional[int]:
    for candidate in candidates:
        for i, h in enumerate(headers):
            if candidate in h:
                return i
    return None


def _parse_mufap_date(val: str) -> Optional[str]:
    """Parse 'Mar 05, 2026' or 'Feb 11, 1996' → ISO '2026-03-05' for correct string comparison."""
    try:
        from datetime import datetime as dt
        return dt.strptime(val.strip(), "%b %d, %Y").strftime("%Y-%m-%d")
    except (ValueError, AttributeError):
        return None


def _to_float(val: str) -> Optional[float]:
    try:
        v = val.strip().replace(",", "")
        return float(v) if v else None
    except (ValueError, TypeError):
        return None
