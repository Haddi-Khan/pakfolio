import time
import json
import concurrent.futures
from typing import Optional, List, Dict
from datetime import datetime

import httpx
from .base import BaseDataProvider, QuoteData, OHLCVPoint, SymbolInfo

import threading
import logging

logger = logging.getLogger(__name__)

BASE_URL = "https://beta-restapi.sarmaaya.pk/api"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

# Global semaphore to prevent hammering Sarmaaya from multiple threads
_sarmaaya_semaphore = threading.Semaphore(10)

class SarmaayaProvider(BaseDataProvider):
    def __init__(self):
        self._client = httpx.Client(headers=HEADERS, timeout=10.0, follow_redirects=True)
        # Small cache to avoid double-fetching during a single page load
        self._quote_cache: Dict[str, tuple[datetime, QuoteData]] = {}
        self._fundamental_cache: Dict[str, tuple[datetime, dict]] = {}
        self._peer_cache: Dict[str, tuple[datetime, list]] = {}
        self._listing_cache: Optional[tuple[datetime, List[SymbolInfo]]] = None
        self._cache_lock = threading.Lock()

    def _get(self, url: str, params: dict = None) -> httpx.Response:
        max_retries = 3
        for attempt in range(max_retries):
            with _sarmaaya_semaphore:
                try:
                    resp = self._client.get(url, params=params)
                    if resp.status_code == 429:
                        # Rate limited, wait briefly and retry
                        wait = (attempt + 1) * 1.5
                        logger.warning(f"Sarmaaya 429 (Rate Limit). Retrying in {wait}s...")
                        time.sleep(wait)
                        continue
                    if resp.status_code == 401:
                        logger.warning("Sarmaaya 401 Unauthorized (likely requires API key). Skipping.")
                        return resp
                    return resp
                except httpx.RequestError as e:
                    if attempt == max_retries - 1: raise
                    time.sleep(1)
        return resp

    def _post(self, url: str, data: dict = None) -> httpx.Response:
        max_retries = 3
        for attempt in range(max_retries):
            with _sarmaaya_semaphore:
                try:
                    resp = self._client.post(url, json=data)
                    if resp.status_code == 429:
                        wait = (attempt + 1) * 2
                        time.sleep(wait)
                        continue
                    return resp
                except httpx.RequestError:
                    if attempt == max_retries - 1: raise
                    time.sleep(1)
        return resp

    def get_quote(self, symbol: str) -> QuoteData:
        upper = symbol.upper().strip()
        now = datetime.now()
        
        # 1. Check cache (5 minute TTL)
        with self._cache_lock:
            if upper in self._quote_cache:
                ts, q = self._quote_cache[upper]
                if (now - ts).total_seconds() < 300:
                    return q

        url = f"{BASE_URL}/stocks/{upper}"
        try:
            resp = self._get(url)
            # Silence 404 for indices being tried as stocks
            if resp.status_code == 404:
                pass
            else:
                resp.raise_for_status()
                data = resp.json()
                if data.get("success"):
                    item = data["response"]
                    price = item.get("close")
                    change = item.get("change")
                    
                    prev_close = None
                    if price is not None and change is not None:
                        prev_close = float(price) - float(change)
                    elif item.get("prev_close"):
                        prev_close = float(item.get("prev_close"))

                    qd = QuoteData(
                        symbol=item.get("symbol", upper),
                        price=price,
                        change=change,
                        change_pct=item.get("change_percentage"),
                        volume=item.get("volume"),
                        open=item.get("open") or item.get("opening_price") or item.get("prev_close"),
                        high=item.get("high"),
                        low=item.get("low"),
                        prev_close=prev_close,
                        name=item.get("name"),
                        isin=item.get("isin"),
                        asset_type="stock",
                        sector_name=item.get("sectorName")
                    )
                    with self._cache_lock:
                        self._quote_cache[upper] = (now, qd)
                    return qd
        except Exception as e:
            # Downgrade to warning as this is now a fallback provider
            logger.debug(f"Sarmaaya quote fetch error for {upper}: {e}")
        
        # 3. Fallback to Indices if stock not found
        try:
            url_indices = f"{BASE_URL}/indices"
            resp = self._get(url_indices)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("success"):
                    indices = data["response"].get("data", [])
                    for idx in indices:
                        if idx.get("symbol") == upper:
                            price = idx.get("curr")
                            change = idx.get("change")
                            prev_close = None
                            if price is not None and change is not None:
                                prev_close = float(price) - float(change)
                            
                            # For indices, Sarmaaya listing lacks OHLC. Try to get it from history for today.
                            open_p, high_p, low_p = None, None, None
                            try:
                                # Fetch last few days history to ensure we get today's latest point
                                end_d = (now + timedelta(days=1)).strftime("%Y-%m-%d")
                                start_d = (now - timedelta(days=5)).strftime("%Y-%m-%d")
                                hist = self.get_historical(upper, start_d, end_d)
                                if hist:
                                    last = hist[-1]
                                    open_p = last.open
                                    high_p = last.high
                                    low_p = last.low
                                    # If history price is more recent than listing, use it
                                    if last.close and (price is None or abs(last.close - price) < 0.001):
                                        price = last.close
                            except Exception as e:
                                logger.debug(f"Failed to fetch index OHLC: {e}")

                            qd = QuoteData(
                                symbol=upper,
                                price=price,
                                change=change,
                                change_pct=idx.get("changePercent"),
                                volume=idx.get("volume"),
                                open=open_p or prev_close or price,
                                high=high_p or price,
                                low=low_p or price,
                                prev_close=prev_close,
                                asset_type="index",
                                name=f"{upper} Index"
                            )
                            with self._cache_lock:
                                self._quote_cache[upper] = (now, qd)
                            return qd
        except Exception as e:
            logger.error(f"Sarmaaya index fallback failed for {upper}: {e}")

        return QuoteData(symbol=symbol.upper())

    def get_quotes_bulk(self, symbols: List[str]) -> Dict[str, QuoteData]:
        # Sarmaaya doesn't have a bulk endpoint, so we parallelize with threads.
        results = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_symbol = {executor.submit(self.get_quote, s): s for s in symbols}
            for future in concurrent.futures.as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                try:
                    results[symbol.upper()] = future.result()
                except Exception:
                    results[symbol.upper()] = QuoteData(symbol=symbol.upper())
        return results

    def get_historical(self, symbol: str, from_date: str, to_date: str) -> List[OHLCVPoint]:
        # Convert date strings (YYYY-MM-DD) to epoch seconds
        try:
            from_ts = int(datetime.strptime(from_date, "%Y-%m-%d").timestamp())
            to_ts = int(datetime.strptime(to_date, "%Y-%m-%d").timestamp())
        except ValueError:
            return []

        url = f"{BASE_URL}/tradingview/history"
        params = {
            "symbol": symbol.upper(),
            "resolution": "D",
            "from": from_ts,
            "to": to_ts
        }
        
        try:
            resp = self._get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            if data.get("success") and data["response"].get("s") == "ok":
                r = data["response"]
                points = []
                for i in range(len(r.get("t", []))):
                    dt = datetime.fromtimestamp(r["t"][i]).strftime("%Y-%m-%d")
                    points.append(OHLCVPoint(
                        date=dt,
                        open=float(r["o"][i]),
                        high=float(r["h"][i]),
                        low=float(r["l"][i]),
                        close=float(r["c"][i]),
                        volume=int(r["v"][i])
                    ))
                return points
        except Exception:
            pass
        return []

    def search_symbols(self, query: str) -> List[SymbolInfo]:
        # We can reuse the all symbols list and filter locally
        all_syms = self.get_all_symbols()
        query = query.upper()
        return [s for s in all_syms if query in s.symbol or query in s.name.upper()]

    def get_all_symbols(self) -> List[SymbolInfo]:
        """Fetch the full list of symbols from the listing API."""
        now = datetime.now()
        with self._cache_lock:
            if self._listing_cache:
                ts, syms = self._listing_cache
                if (now - ts).total_seconds() < 3600: # 1 hour cache
                    return syms

        url = f"{BASE_URL}/stocks/listing?limit=1000"
        try:
            resp = self._get(url)
            resp.raise_for_status()
            data = resp.json().get("response", {})
            stocks = data.get("data", [])
            
            syms = [
                SymbolInfo(
                    symbol=s.get("symbol"),
                    name=s.get("name"),
                    asset_type="stock"
                )
                for s in stocks if s.get("symbol")
            ]
            with self._cache_lock:
                self._listing_cache = (now, syms)
            return syms
        except Exception:
            return []

    # Extra methods specific to Sarmaaya for detailed pages
    def get_fundamentals(self, isin: str) -> dict:
        now = datetime.now()
        with self._cache_lock:
            if isin in self._fundamental_cache:
                ts, data = self._fundamental_cache[isin]
                if (now - ts).total_seconds() < 86400: # 24 hour cache
                    return data

        url = f"{BASE_URL}/stocks/fundamentals/ratios"
        params = {"isin": isin, "periodicity": "ANN"}
        try:
            resp = self._get(url, params=params)
            resp.raise_for_status()
            data = resp.json().get("response", {})
            
            # Pivot data from {Ratio: {data: [{year, value}]}} to {Year: {Ratio: Value}}
            pivoted = {}
            for ratio_name, ratio_info in data.items():
                if isinstance(ratio_info, dict) and "data" in ratio_info:
                    for entry in ratio_info["data"]:
                        year = entry.get("year")
                        value = entry.get("value")
                        if year:
                            ys = str(year)
                            if ys not in pivoted:
                                pivoted[ys] = {}
                            pivoted[ys][ratio_name] = value
            
            # Sort years descending
            sorted_years = sorted(pivoted.keys(), reverse=True)
            res = {y: pivoted[y] for y in sorted_years}
            with self._cache_lock:
                self._fundamental_cache[isin] = (now, res)
            return res
        except Exception:
            return {}

    def get_peers(self, symbol: str) -> list:
        # Tried specific peers-data but it returned fundamentals for the same stock.
        # Using the listing API as a reliable source of other stocks to show.
        url = f"{BASE_URL}/stocks/listing"
        try:
            resp = self._get(url)
            resp.raise_for_status()
            data = resp.json().get("response", {})
            stocks = data.get("data", [])
            
            # Map Sarmaaya listing fields to what our frontend expects
            mapped = []
            for s in stocks:
                if s.get("symbol", "").upper() == symbol.upper():
                    continue
                mapped.append({
                    "symbol": s.get("symbol"),
                    "name": s.get("name"),
                    "price": s.get("close"),
                    "change": s.get("change"),
                    "change_pct": s.get("changePercent"),
                    "logo": s.get("logo")
                })
            return mapped[:6] # Return top 6
        except Exception:
            return []
