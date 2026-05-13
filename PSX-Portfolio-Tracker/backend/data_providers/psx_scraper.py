"""PSX Data Provider — scrapes dps.psx.com.pk (same source Sarmaya uses).

Endpoints used:
  GET https://dps.psx.com.pk/quotes          → market-wide quotes JSON
  GET https://dps.psx.com.pk/timeseries/eod/{SYMBOL}  → EOD history
  GET https://dps.psx.com.pk/company/{SYMBOL}          → company detail page (HTML)

Rate limiting: 1 req/sec soft limit to avoid IP bans.
For production, swap to PSXTerminal WebSocket or CapitalStake API.
"""

import time
import re
import logging
import random
import os
import contextlib
from typing import Optional, List, Dict
from functools import lru_cache

import httpx
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import psxdata
import yfinance as yf
import pandas as pd
from sqlalchemy.dialects.postgresql import insert as pg_insert

from .base import BaseDataProvider, QuoteData, OHLCVPoint, SymbolInfo
from models import HistoryPSX
from database import SessionLocal

logger = logging.getLogger(__name__)

# Completely silence yfinance's built-in logger to prevent annoying 404/delisted errors
logging.getLogger('yfinance').setLevel(logging.CRITICAL)

BASE = "https://dps.psx.com.pk"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; PSXTracker/1.0)",
    "Accept": "application/json, text/html",
}
TIMEOUT = 10


class PSXScraper(BaseDataProvider):

    def __init__(self):
        self._client = httpx.Client(headers=HEADERS, timeout=TIMEOUT, follow_redirects=True)
        self._last_request = 0.0
        self._cache: Dict[str, QuoteData] = {}
        self._cache_time = 0.0

    def _get(self, url: str, params: dict = None) -> httpx.Response:
        # soft rate limit
        elapsed = time.time() - self._last_request
        if elapsed < 0.5:
            time.sleep(0.5 - elapsed)
        self._last_request = time.time()
        return self._client.get(url, params=params)

    # ── Quotes ────────────────────────────────────────────────────────────────

    def get_quote(self, symbol: str) -> QuoteData:
        bulk = self.get_quotes_bulk([symbol])
        return bulk.get(symbol.upper(), QuoteData(symbol=symbol.upper()))

    def get_quotes_bulk(self, symbols: List[str]) -> Dict[str, QuoteData]:
        """
        PSX quotes endpoint returns all listed stocks.
        We filter to the requested symbols client-side.
        """
        upper = {s.upper() for s in symbols}
        
        # Check cache (10 minute TTL)
        now = time.time()
        if now - self._cache_time < 600 and self._cache:
            return {s: self._cache[s] for s in upper if s in self._cache}

        result: Dict[str, QuoteData] = {}

        try:
            resp = self._get(f"{BASE}/quotes")
            resp.raise_for_status()
            data = resp.json()

            # Response is a list of dicts with keys: symbol, ldcp, currentprice, change, volume etc.
            # Field names vary — handle both possible shapes
            for item in data:
                sym = (item.get("symbol") or item.get("SYMBOL") or "").upper()
                # Store everything in cache
                price = _to_float(item.get("currentprice") or item.get("close") or item.get("CURRENT_PRICE"))
                prev  = _to_float(item.get("ldcp") or item.get("LDCP") or item.get("prev_close"))
                change = _to_float(item.get("change") or item.get("CHANGE"))
                if change is None and price is not None and prev is not None:
                    change = price - prev
                change_pct = None
                if change is not None and prev and prev != 0:
                    change_pct = (change / prev) * 100

                qd = QuoteData(
                    symbol=sym,
                    price=price,
                    change=change,
                    change_pct=change_pct,
                    volume=_to_int(item.get("volume") or item.get("VOLUME")),
                    open=_to_float(item.get("open") or item.get("OPEN")),
                    high=_to_float(item.get("high") or item.get("HIGH")),
                    low=_to_float(item.get("low") or item.get("LOW")),
                    prev_close=prev,
                    asset_type=item.get("asset_type", "STOCK")
                )
                self._cache[sym] = qd
                if sym in upper:
                    result[sym] = qd
            
            self._cache_time = now
        except Exception:
            pass

        # For any symbol not found in bulk, try individual fallback
        for sym in upper:
            if sym not in result:
                result[sym] = self._get_quote_fallback(sym)

        return result

    def _get_quote_fallback(self, symbol: str) -> QuoteData:
        """Scrape the company page for price when bulk endpoint misses a symbol."""
        try:
            resp = self._get(f"{BASE}/company/{symbol}")
            resp.raise_for_status()
            html = resp.text
            # Extract price from <div class="quote__close">Rs. 93.85</div>
            m = re.search(r'quote__close[^>]*>[^<]*Rs\.?\s*([\d,]+\.?\d*)', html)
            price = float(m.group(1).replace(",", "")) if m else None
            # Extract change
            m2 = re.search(r'quote__change[^>]*>([-+]?[\d,]+\.?\d*)', html)
            change = float(m2.group(1).replace(",", "")) if m2 else None
            
            # Extract open, high, low, volume
            m_open = re.search(r'<div class="stats_label">\s*Open\s*</div>\s*<div class="stats_value">\s*([\d,.]+)\s*</div>', html)
            open_price = float(m_open.group(1).replace(",", "")) if m_open else None
            
            m_high = re.search(r'<div class="stats_label">\s*High\s*</div>\s*<div class="stats_value">\s*([\d,.]+)\s*</div>', html)
            high_price = float(m_high.group(1).replace(",", "")) if m_high else None
            
            m_low = re.search(r'<div class="stats_label">\s*Low\s*</div>\s*<div class="stats_value">\s*([\d,.]+)\s*</div>', html)
            low_price = float(m_low.group(1).replace(",", "")) if m_low else None
            
            m_vol = re.search(r'<div class="stats_label">\s*Volume\s*</div>\s*<div class="stats_value">\s*([\d,.]+)\s*</div>', html)
            volume = int(m_vol.group(1).replace(",", "")) if m_vol else None

            prev_close = None
            if price is not None and change is not None:
                prev_close = price - change

            return QuoteData(
                symbol=symbol, 
                price=price, 
                change=change,
                open=open_price,
                high=high_price,
                low=low_price,
                volume=volume,
                prev_close=prev_close,
                asset_type="STOCK"
            )
        except Exception:
            return QuoteData(symbol=symbol)

    # ── Historical ────────────────────────────────────────────────────────────

    def get_historical(self, symbol: str, from_date: str, to_date: str) -> List[OHLCVPoint]:
        try:
            resp = self._get(
                f"{BASE}/timeseries/eod/{symbol.upper()}",
                params={"from": from_date, "to": to_date},
            )
            resp.raise_for_status()
            data = resp.json()
            points = []
            for row in data:
                # row shape: [timestamp_ms, open, high, low, close, volume]
                # or dict with keys
                if isinstance(row, list) and len(row) >= 5:
                    ts = row[0]
                    dt = _ts_to_date(ts)
                    points.append(OHLCVPoint(
                        date=dt,
                        open=float(row[1] or 0),
                        high=float(row[2] or 0),
                        low=float(row[3] or 0),
                        close=float(row[4] or 0),
                        volume=int(row[5] or 0) if len(row) > 5 else 0,
                    ))
                elif isinstance(row, dict):
                    points.append(OHLCVPoint(
                        date=str(row.get("date") or row.get("DATE") or ""),
                        open=float(row.get("open") or 0),
                        high=float(row.get("high") or 0),
                        low=float(row.get("low") or 0),
                        close=float(row.get("close") or row.get("CLOSE") or 0),
                        volume=int(row.get("volume") or 0),
                    ))
            return sorted(points, key=lambda p: p.date)
        except Exception:
            return []

    # ── Symbol Search ─────────────────────────────────────────────────────────

    def search_symbols(self, query: str) -> List[SymbolInfo]:
        all_syms = self.get_all_symbols()
        q = query.lower()
        return [s for s in all_syms if q in s.symbol.lower() or q in (s.name or "").lower()][:20]

    @lru_cache(maxsize=1)
    def get_all_symbols(self) -> List[SymbolInfo]:
        try:
            resp = self._get(f"{BASE}/symbols")
            resp.raise_for_status()
            data = resp.json()
            results = []
            for item in data:
                # Exclude bonds/debt instruments
                if item.get("isDebt", False):
                    continue
                
                sym = item.get("symbol") or item.get("SYMBOL") or ""
                name = item.get("name") or item.get("NAME") or item.get("company") or sym
                if sym:
                    atype = "ETF" if "ETF" in sym.upper() or "ETF" in name.upper() else "STOCK"
                    results.append(SymbolInfo(symbol=sym.upper(), name=name, asset_type=atype))
            return results
        except Exception:
            # fallback: return hardcoded common PSX symbols
            return _FALLBACK_SYMBOLS


# ── helpers ───────────────────────────────────────────────────────────────────

def _to_float(val) -> Optional[float]:
    try:
        return float(str(val).replace(",", "")) if val is not None else None
    except (ValueError, TypeError):
        return None


def _to_int(val) -> Optional[int]:
    try:
        return int(float(str(val).replace(",", ""))) if val is not None else None
    except (ValueError, TypeError):
        return None


def _ts_to_date(ts) -> str:
    """Convert epoch ms or epoch s to ISO date string."""
    try:
        ts = int(ts)
        if ts > 1e10:
            ts = ts // 1000
        from datetime import date
        import datetime as dt
        return dt.date.fromtimestamp(ts).isoformat()
    except Exception:
        return ""


_FALLBACK_SYMBOLS = [
    SymbolInfo("NPL",     "Nishat Power Limited", asset_type="STOCK"),
    SymbolInfo("BIPL",    "BankIslami Pakistan Limited", asset_type="STOCK"),
    SymbolInfo("HALEON",  "Haleon Pakistan Limited", asset_type="STOCK"),
    SymbolInfo("NCPL",    "Nishat Chunian Power Limited", asset_type="STOCK"),
    SymbolInfo("HUBC",    "The Hub Power Company Limited", asset_type="STOCK"),
    SymbolInfo("FFC",     "Fauji Fertilizer Company Limited", asset_type="STOCK"),
    SymbolInfo("AVN",     "Avanceon Limited", asset_type="STOCK"),
    SymbolInfo("MEBL",    "Meezan Bank Limited", asset_type="STOCK"),
    SymbolInfo("MZNPETF", "Meezan Pakistan ETF", asset_type="ETF"),
    SymbolInfo("LUCK",    "Lucky Cement Limited", asset_type="STOCK"),
    SymbolInfo("ENGRO",   "Engro Corporation Limited", asset_type="STOCK"),
    SymbolInfo("HBL",     "Habib Bank Limited", asset_type="STOCK"),
    SymbolInfo("MCB",     "MCB Bank Limited", asset_type="STOCK"),
    SymbolInfo("UBL",     "United Bank Limited", asset_type="STOCK"),
    SymbolInfo("PSO",     "Pakistan State Oil", asset_type="STOCK"),
    SymbolInfo("OGDC",    "Oil & Gas Development Company", asset_type="STOCK"),
    SymbolInfo("PPL",     "Pakistan Petroleum Limited", asset_type="STOCK"),
    SymbolInfo("MARI",    "Mari Petroleum Company Limited", asset_type="STOCK"),
    SymbolInfo("SYS",     "Systems Limited", asset_type="STOCK"),
    SymbolInfo("TRG",     "TRG Pakistan Limited", asset_type="STOCK"),
    SymbolInfo("SEARL",   "The Searle Company Limited", asset_type="STOCK"),
    SymbolInfo("EFERT",   "Engro Fertilizers Limited", asset_type="STOCK"),
    SymbolInfo("FATIMA",  "Fatima Fertilizer Company Limited", asset_type="STOCK"),
    SymbolInfo("MLCF",    "Maple Leaf Cement Factory", asset_type="STOCK"),
    SymbolInfo("KOHC",    "Kohat Cement Company Limited", asset_type="STOCK"),
]

# ── Bulk Historical Scraper (Merged) ──────────────────────────────────────────

def _get_robust_session(proxy=None):
    session = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"]
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "X-Requested-With": "XMLHttpRequest",
        "Origin": "https://dps.psx.com.pk",
        "Referer": "https://dps.psx.com.pk/symbols",
    })
    if proxy:
        session.proxies = {"http": proxy, "https": proxy}
    return session

def _fetch_psx_history(session, symbol):
    url = "https://dps.psx.com.pk/historical"
    data = {"symbol": symbol}
    response = session.post(url, data=data, timeout=30)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.text, 'html.parser')
    rows = soup.find_all('tr')
    if not rows:
        return pd.DataFrame()
        
    parsed_data = []
    for row in rows:
        cols = row.find_all('td')
        if len(cols) >= 6:
            parsed_data.append({
                "Date": cols[0].text.strip(),
                "Open": cols[1].text.strip().replace(',', ''),
                "High": cols[2].text.strip().replace(',', ''),
                "Low": cols[3].text.strip().replace(',', ''),
                "Close": cols[4].text.strip().replace(',', ''),
                "Volume": cols[5].text.strip().replace(',', '')
            })
            
    df = pd.DataFrame(parsed_data)
    if not df.empty:
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        for col in ['Open', 'High', 'Low', 'Close']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df['Volume'] = pd.to_numeric(df['Volume'], errors='coerce')
        df = df.dropna(subset=['Date']).sort_values('Date').reset_index(drop=True)
    return df

def _fetch_yf_history(symbol):
    yf_symbol = f"{symbol}.KA"
    try:
        # Suppress yfinance console output/errors for missing symbols
        with open(os.devnull, 'w') as devnull:
            with contextlib.redirect_stdout(devnull), contextlib.redirect_stderr(devnull):
                df = yf.download(yf_symbol, period="max", progress=False)

        if df.empty: return pd.DataFrame()
        df = df.reset_index()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)
        expected_cols = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
        if any(c not in df.columns for c in expected_cols):
            return pd.DataFrame()
        df = df[expected_cols].copy()
        if pd.api.types.is_datetime64tz_dtype(df['Date']):
            df['Date'] = df['Date'].dt.tz_localize(None)
        for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df = df.dropna(subset=['Date']).sort_values('Date').reset_index(drop=True)
        return df
    except Exception as e:
        logger.debug(f"Yahoo Finance fetch failed for {symbol}: {e}")
        return pd.DataFrame()

def _calculate_technical_indicators(df):
    """Calculates RSI, MA, and Bollinger Bands manually using pandas."""
    if df.empty or len(df) < 20:
        return df
    try:
        for col in ["Open", "High", "Low", "Close", "Volume"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        # SMA 50 and 200
        df["SMA_50"] = df["Close"].rolling(window=50).mean()
        df["SMA_200"] = df["Close"].rolling(window=200).mean()

        # Bollinger Bands (20, 2)
        df["SMA_20"] = df["Close"].rolling(window=20).mean()
        df["STD_20"] = df["Close"].rolling(window=20).std()
        df["BBL_20_2.0"] = df["SMA_20"] - (df["STD_20"] * 2)
        df["BBU_20_2.0"] = df["SMA_20"] + (df["STD_20"] * 2)

        # RSI 14
        delta = df["Close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df["RSI_14"] = 100 - (100 / (1 + rs))

    except Exception as e:
        logger.error(f"Error calculating technicals: {e}")
    return df

def scrape_all_history(proxies=None, subset_limit=None):
    """
    Scrapes history for PSX symbols and saves them to the history_psx table in Postgres.
    """
    logger.info("Fetching list of PSX symbols...")
    scraper = PSXScraper()
    symbol_infos = scraper.get_all_symbols()
    
    # Create a mapping of symbol -> name
    name_map = {s.symbol: s.name for s in symbol_infos}
    symbols = [s.symbol for s in symbol_infos]
    
    if subset_limit:
        symbols = symbols[:subset_limit]

    proxies = proxies or []
    proxy_index = 0
    total_proxies = len(proxies)
    
    db = SessionLocal()
    try:
        for i, symbol in enumerate(symbols):
            logger.info(f"[{i+1}/{len(symbols)}] Processing {symbol}...")
            sym_name = name_map.get(symbol, symbol)
            
            # Check if we already have recent data
            # To avoid re-downloading max if we already have it, we could query the DB:
            # last_date = db.query(func.max(HistoryPSX.date)).filter_by(symbol=symbol).scalar()
            # If doing incremental updates, this would be where we skip if last_date is recent.
            # But the original script just checked if any data existed before 2016.
            
            proxy = proxies[proxy_index % total_proxies] if total_proxies > 0 else None
            session = _get_robust_session(proxy)
            
            try:
                df_psx = _fetch_psx_history(session, symbol)
                df_yf = _fetch_yf_history(symbol)
                
                df_combined = pd.DataFrame()
                if not df_psx.empty and not df_yf.empty:
                    df_combined = pd.concat([df_psx, df_yf])
                    df_combined = df_combined.drop_duplicates(subset=['Date'], keep='first')
                    df_combined = df_combined.sort_values('Date').reset_index(drop=True)
                elif not df_psx.empty:
                    df_combined = df_psx
                elif not df_yf.empty:
                    df_combined = df_yf

                if df_combined.empty:
                    logger.warning(f"No equity data found for {symbol}.")
                else:
                    # Calculate technical indicators
                    df_combined = _calculate_technical_indicators(df_combined)
                    
                    # We handle NaNs during dict construction to avoid Pandas dtype coercion issues
                    
                    objects_to_add = []
                    for row in df_combined.to_dict('records'):
                        dt = row['Date'].to_pydatetime().date()
                        
                        def clean(val):
                            return None if pd.isna(val) else val
                            
                        objects_to_add.append({
                            "symbol": symbol,
                            "symbol_name": sym_name,
                            "date": dt,
                            "open": clean(row.get('Open')),
                            "high": clean(row.get('High')),
                            "low": clean(row.get('Low')),
                            "close": clean(row.get('Close')),
                            "volume": clean(row.get('Volume')),
                            "sma_50": clean(row.get('SMA_50')),
                            "sma_200": clean(row.get('SMA_200')),
                            "sma_20": clean(row.get('SMA_20')),
                            "std_20": clean(row.get('STD_20')),
                            "bbl_20_2_0": clean(row.get('BBL_20_2.0')),
                            "bbu_20_2_0": clean(row.get('BBU_20_2.0')),
                            "rsi_14": clean(row.get('RSI_14'))
                        })
                    
                    if objects_to_add:
                        # Use Postgres upsert to keep previous data and update existing
                        stmt = pg_insert(HistoryPSX).values(objects_to_add)
                        update_dict = {
                            "open": stmt.excluded.open,
                            "high": stmt.excluded.high,
                            "low": stmt.excluded.low,
                            "close": stmt.excluded.close,
                            "volume": stmt.excluded.volume,
                            "sma_50": stmt.excluded.sma_50,
                            "sma_200": stmt.excluded.sma_200,
                            "sma_20": stmt.excluded.sma_20,
                            "std_20": stmt.excluded.std_20,
                            "bbl_20_2_0": stmt.excluded.bbl_20_2_0,
                            "bbu_20_2_0": stmt.excluded.bbu_20_2_0,
                            "rsi_14": stmt.excluded.rsi_14,
                        }
                        stmt = stmt.on_conflict_do_update(
                            index_elements=['symbol', 'date'],
                            set_=update_dict
                        )
                        db.execute(stmt)
                        db.commit()
                        logger.info(f"Successfully saved/upserted {len(objects_to_add)} records for {symbol} to DB.")
                        
                time.sleep(random.uniform(1.0, 3.0))
                if total_proxies > 0:
                    proxy_index += 1
                    
            except Exception as e:
                logger.error(f"Failed to fetch data for {symbol}: {e}")
                db.rollback()
                
    finally:
        db.close()
