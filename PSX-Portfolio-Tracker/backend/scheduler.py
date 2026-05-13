"""
PSX Data Scheduler
==================
Manages all background data sync jobs:

  Every 10 min (market hours, Mon–Fri 9:30–15:30 PKT):
    - Refresh live prices for all equity symbols
    - Update KSE-100 index value

  Nightly at 02:00 PKT (after market close):
    - Append today's EOD prices to historical_prices for all symbols
    - Fetch all mutual fund NAVs → save to live_prices
    - Save portfolio snapshots for all active portfolios

PSX market timezone: Asia/Karachi (PKT = UTC+5, no DST)
"""

import logging
import re
from datetime import date, timedelta, datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

logger = logging.getLogger(__name__)

PKT = pytz.timezone("Asia/Karachi")

# PSX market hours (PKT)
MARKET_OPEN_H, MARKET_OPEN_M   = 9, 30
MARKET_CLOSE_H, MARKET_CLOSE_M = 15, 30

PSX_BASE = "https://dps.psx.com.pk"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; PSXTracker/1.0)",
    "Accept": "application/json, text/html",
}
PRICE_WORKERS = 10


def _is_market_open() -> bool:
    """Return True if PSX is currently open."""
    now = datetime.now(PKT)
    if now.weekday() >= 5:  # Saturday=5, Sunday=6
        return False
    open_t  = now.replace(hour=MARKET_OPEN_H,  minute=MARKET_OPEN_M,  second=0, microsecond=0)
    close_t = now.replace(hour=MARKET_CLOSE_H, minute=MARKET_CLOSE_M, second=0, microsecond=0)
    return open_t <= now <= close_t


def _to_float(v):
    try:
        return float(str(v).replace(",", "")) if v is not None and v != "" else None
    except (TypeError, ValueError):
        return None


# ── Price scraping ─────────────────────────────────────────────────────────────

def _scrape_price(symbol: str, client: httpx.Client):
    """Scrape current close price from PSX company page."""
    try:
        r = client.get(f"{PSX_BASE}/company/{symbol}", timeout=12)
        if r.status_code != 200:
            return symbol, None
        html = r.text
        m = re.search(r'quote__close[^>]*>[^<]*Rs\.?\s*([\d,]+\.?\d*)', html)
        price = _to_float(m.group(1)) if m else None
        m_chg_val = re.search(r'change__value[^>]*>([-+]?[\d,]+\.?\d*)', html)
        if m_chg_val:
            change_val = _to_float(m_chg_val.group(1))
            if 'change__text--neg' in html[html.find('quote__change'):html.find('change__percent')]:
                change_val = -change_val
            change = change_val
        else:
            change = None
        
        m_open = re.search(r'<div class="stats_label">\s*Open\s*</div>\s*<div class="stats_value">\s*([\d,.]+)\s*</div>', html, re.S)
        open_price = _to_float(m_open.group(1)) if m_open else None
        
        m_high = re.search(r'<div class="stats_label">\s*High\s*</div>\s*<div class="stats_value">\s*([\d,.]+)\s*</div>', html, re.S)
        high_price = _to_float(m_high.group(1)) if m_high else None
        
        m_low = re.search(r'<div class="stats_label">\s*Low\s*</div>\s*<div class="stats_value">\s*([\d,.]+)\s*</div>', html, re.S)
        low_price = _to_float(m_low.group(1)) if m_low else None
        
        m_vol = re.search(r'<div class="stats_label">\s*Volume\s*</div>\s*<div class="stats_value">\s*([\d,.]+)\s*</div>', html, re.S)
        volume = _to_float(m_vol.group(1)) if m_vol else None

        return symbol, {
            "price": price, "change": change, 
            "open": open_price, "high": high_price, 
            "low": low_price, "volume": volume
        }
    except Exception:
        return symbol, None


def _fetch_all_equity_prices() -> dict:
    """Concurrently scrape live prices for all equity symbols from PSX."""
    try:
        with httpx.Client(headers=HEADERS, timeout=15, follow_redirects=True) as c:
            r = c.get(f"{PSX_BASE}/symbols")
            r.raise_for_status()
            symbols_data = r.json()
    except Exception as e:
        logger.error(f"Scheduler: failed to fetch symbol list: {e}")
        return {}

    equity_syms = [
        item["symbol"].strip().upper()
        for item in symbols_data
        if item.get("symbol") and not item.get("isDebt", False)
    ]

    results = {}
    with httpx.Client(headers=HEADERS, timeout=12, follow_redirects=True) as client:
        with ThreadPoolExecutor(max_workers=PRICE_WORKERS) as pool:
            futures = {pool.submit(_scrape_price, sym, client): sym for sym in equity_syms}
            for future in as_completed(futures):
                sym, data = future.result()
                if data and data.get("price") is not None:
                    results[sym] = data
    return results


# ── Scheduler jobs ─────────────────────────────────────────────────────────────

def job_refresh_live_prices():
    """10-min job: refresh all equity live prices + update sector/name from /symbols."""
    if not _is_market_open():
        logger.debug("Scheduler: market closed, skipping live price refresh")
        return

    logger.info("Scheduler: refreshing live prices...")
    prices = _fetch_all_equity_prices()
    if not prices:
        logger.warning("Scheduler: no prices fetched")
        return

    from database import SessionLocal
    from sqlalchemy import text
    db = SessionLocal()
    try:
        # Also refresh symbol names/sectors from /symbols in same pass
        with httpx.Client(headers=HEADERS, timeout=15, follow_redirects=True) as c:
            r = c.get(f"{PSX_BASE}/symbols")
            symbols_meta = {
                item["symbol"].strip().upper(): item
                for item in r.json()
                if item.get("symbol")
            } if r.status_code == 200 else {}

        batch_params = {}
        value_clauses = []
        for i, (sym, data) in enumerate(prices.items()):
            price  = data["price"]
            change = data.get("change")

            # Compute prev_close and change_pct from what we have
            prev_close = None
            change_pct = None
            if price is not None and change is not None:
                prev_close = round(price - change, 4)
                if prev_close and prev_close != 0:
                    change_pct = round((change / prev_close) * 100, 4)

            batch_params[f"s{i}"]  = sym
            batch_params[f"p{i}"]  = price
            batch_params[f"c{i}"]  = change
            batch_params[f"cp{i}"] = change_pct
            batch_params[f"pc{i}"] = prev_close
            batch_params[f"o{i}"]  = data.get("open")
            batch_params[f"h{i}"]  = data.get("high")
            batch_params[f"l{i}"]  = data.get("low")
            batch_params[f"v{i}"]  = data.get("volume")
            batch_params["now"] = datetime.utcnow()
            value_clauses.append(
                f"(:s{i}, :p{i}, :c{i}, :cp{i}, :pc{i}, :o{i}, :h{i}, :l{i}, :v{i}, :now)"
            )

        if value_clauses:
            # Chunk into batches of 20 to stay under Supabase's statement timeout
            CHUNK = 20
            all_syms = list(prices.items())
            for chunk_start in range(0, len(all_syms), CHUNK):
                chunk = all_syms[chunk_start:chunk_start + CHUNK]
                batch_params = {"now": datetime.utcnow()}
                chunk_clauses = []
                for i, (sym, data) in enumerate(chunk):
                    price  = data["price"]
                    change = data.get("change")
                    prev_close = None
                    change_pct = None
                    if price is not None and change is not None:
                        prev_close = round(price - change, 4)
                        if prev_close and prev_close != 0:
                            change_pct = round((change / prev_close) * 100, 4)
                    batch_params[f"s{i}"]  = sym
                    batch_params[f"p{i}"]  = price
                    batch_params[f"c{i}"]  = change
                    batch_params[f"cp{i}"] = change_pct
                    batch_params[f"pc{i}"] = prev_close
                    batch_params[f"o{i}"]  = data.get("open")
                    batch_params[f"h{i}"]  = data.get("high")
                    batch_params[f"l{i}"]  = data.get("low")
                    batch_params[f"v{i}"]  = data.get("volume")
                    chunk_clauses.append(
                        f"(:s{i}, :p{i}, :c{i}, :cp{i}, :pc{i}, :o{i}, :h{i}, :l{i}, :v{i}, :now)"
                    )
                try:
                    db.execute(text(f"""
                        INSERT INTO live_prices (symbol, price, change, change_pct, prev_close, open, high, low, volume, updated_at)
                        VALUES {', '.join(chunk_clauses)}
                        ON CONFLICT (symbol) DO UPDATE SET
                            price      = EXCLUDED.price,
                            change     = EXCLUDED.change,
                            change_pct = EXCLUDED.change_pct,
                            prev_close = EXCLUDED.prev_close,
                            open       = EXCLUDED.open,
                            high       = EXCLUDED.high,
                            low        = EXCLUDED.low,
                            volume     = EXCLUDED.volume,
                            updated_at = :now
                    """), batch_params)
                    db.commit()
                except Exception as chunk_err:
                    logger.warning(f"Scheduler: live price chunk failed (skipping): {chunk_err}")
                    db.rollback()

        logger.info(f"Scheduler: live prices updated ({len(prices)} symbols)")
    except Exception as e:
        logger.error(f"Scheduler: live price refresh failed: {e}")
        db.rollback()
    finally:
        db.close()



def job_nightly_eod():
    """Nightly job: append today's EOD prices to historical_prices for all symbols."""
    logger.info("Scheduler: running nightly EOD sync...")
    from database import SessionLocal
    from models import AssetType, HistoricalPrice
    from sqlalchemy import text

    today = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()

    try:
        with httpx.Client(headers=HEADERS, timeout=15, follow_redirects=True) as c:
            r = c.get(f"{PSX_BASE}/symbols")
            r.raise_for_status()
            symbols_data = r.json()
    except Exception as e:
        logger.error(f"Scheduler: EOD sync - failed to get symbol list: {e}")
        return

    equity_syms = [
        item["symbol"].strip().upper()
        for item in symbols_data
        if item.get("symbol") and not item.get("isDebt", False)
    ]

    db = SessionLocal()
    saved = 0
    try:
        # Scrape all prices (same as live refresh)
        prices = _fetch_all_equity_prices()

        rows = []
        for sym, data in prices.items():
            if data.get("price") is None:
                continue
            rows.append((sym, today, data["price"]))

        # Batch upsert into historical_prices
        CHUNK = 200
        for i in range(0, len(rows), CHUNK):
            chunk = rows[i:i + CHUNK]
            params = {}
            value_clauses = []
            for j, (sym, dt, price) in enumerate(chunk):
                params[f"s{j}"] = sym
                params[f"d{j}"] = dt
                params[f"p{j}"] = price
                value_clauses.append(f"(:s{j}, :d{j}, :p{j}, CAST('STOCK' AS assettype))")
            db.execute(text(f"""
                INSERT INTO historical_prices (symbol, date, price, asset_type)
                VALUES {', '.join(value_clauses)}
                ON CONFLICT (symbol, date) DO UPDATE SET
                    price = EXCLUDED.price
            """), params)
            
            # Also append to HistoryPSX
            psx_value_clauses = []
            for j in range(len(chunk)):
                psx_value_clauses.append(f"(:s{j}, :d{j}, :p{j})")
            db.execute(text(f"""
                INSERT INTO history_psx (symbol, date, close)
                VALUES {', '.join(psx_value_clauses)}
                ON CONFLICT (symbol, date) DO UPDATE SET
                    close = EXCLUDED.close
            """), params)

            db.commit()
            saved += len(chunk)

        logger.info(f"Scheduler: EOD sync complete — {saved} rows written for {today}")

        # --- NEW: Calculate Indicators for updated symbols ---
        logger.info("Scheduler: calculating technical indicators for updated symbols...")
        try:
            import pandas as pd
            from database import engine as db_engine
            from sqlalchemy import text as sql_text

            updated_symbols = list(set(r[0] for r in rows))
            with db_engine.connect() as ind_conn:
                for sym in updated_symbols:
                    try:
                        df = pd.read_sql(
                            sql_text(
                                "SELECT id, date, close FROM history_psx "
                                "WHERE symbol = :sym ORDER BY date ASC LIMIT 300"
                            ),
                            ind_conn,
                            params={"sym": sym},
                        )
                        if len(df) < 20:
                            continue

                        df["sma_20"]     = df["close"].rolling(window=20).mean()
                        df["sma_50"]     = df["close"].rolling(window=50).mean()
                        df["sma_200"]    = df["close"].rolling(window=200).mean()
                        df["std_20"]     = df["close"].rolling(window=20).std()
                        df["bbu_20_2_0"] = df["sma_20"] + df["std_20"] * 2
                        df["bbl_20_2_0"] = df["sma_20"] - df["std_20"] * 2

                        # RSI-14
                        delta = df["close"].diff()
                        gain  = delta.clip(lower=0).rolling(14).mean()
                        loss  = (-delta.clip(upper=0)).rolling(14).mean()
                        df["rsi_14"] = 100 - (100 / (1 + gain / loss.replace(0, float("nan"))))

                        latest = df.iloc[-1]

                        def _safe(v):
                            import math
                            return None if (v is None or (isinstance(v, float) and math.isnan(v))) else float(v)

                        ind_conn.execute(sql_text("""
                            UPDATE history_psx SET
                                sma_20     = :s20,
                                sma_50     = :s50,
                                sma_200    = :s200,
                                bbu_20_2_0 = :bbu,
                                bbl_20_2_0 = :bbl,
                                rsi_14     = :rsi
                            WHERE id = :id
                        """), {
                            "s20":  _safe(latest["sma_20"]),
                            "s50":  _safe(latest["sma_50"]),
                            "s200": _safe(latest["sma_200"]),
                            "bbu":  _safe(latest["bbu_20_2_0"]),
                            "bbl":  _safe(latest["bbl_20_2_0"]),
                            "rsi":  _safe(latest["rsi_14"]),
                            "id":   int(latest["id"]),
                        })
                    except Exception as sym_err:
                        logger.warning(f"Scheduler: indicator update failed for {sym}: {sym_err}")

                ind_conn.commit()
            logger.info(f"Scheduler: indicators updated for {len(updated_symbols)} symbols")
        except Exception as e:
            logger.error(f"Scheduler: indicator calculation failed: {e}")


        # After saving EOD prices, recompute change/change_pct in live_prices
        # using yesterday's historical close as prev_close
        db.execute(text("""
            UPDATE live_prices lp
            SET
                prev_close = h.price,
                change     = ROUND(CAST(lp.price - h.price AS numeric), 4),
                change_pct = ROUND(CAST((lp.price - h.price) / NULLIF(h.price, 0) * 100 AS numeric), 4)
            FROM historical_prices h
            WHERE h.symbol = lp.symbol
              AND h.date = (
                  SELECT MAX(date) FROM historical_prices h2
                  WHERE h2.symbol = lp.symbol AND h2.date < CURRENT_DATE
              )
              AND lp.price IS NOT NULL AND h.price IS NOT NULL AND h.price > 0
        """))
        db.commit()
        logger.info("Scheduler: change/change_pct refreshed from historical prev_close")

    except Exception as e:
        logger.error(f"Scheduler: EOD sync failed: {e}")
        db.rollback()
    finally:
        db.close()


def job_refresh_kse100():
    """Fetch today's KSE-100 index value and append to historical_prices."""
    logger.info("Scheduler: refreshing KSE-100 index...")
    from database import SessionLocal
    from data_providers.composite_provider import CompositeProvider
    from sqlalchemy import text

    today = date.today().isoformat()
    start = (date.today() - timedelta(days=7)).isoformat()

    db = SessionLocal()
    try:
        provider = CompositeProvider()
        points = provider.get_historical("KSE100", start, today)
        
        if not points:
            logger.info("Scheduler: Sarmaaya KSE-100 fetch failed, trying Yahoo Finance fallback...")
            import yfinance as yf
            ticker = yf.Ticker("^KSE100")
            hist = ticker.history(start=start, end=today)
            if not hist.empty:
                from data_providers.base import OHLCVPoint
                points = [
                    OHLCVPoint(
                        date=index.strftime("%Y-%m-%d"),
                        open=row['Open'], high=row['High'],
                        low=row['Low'], close=row['Close'],
                        volume=int(row['Volume'])
                    )
                    for index, row in hist.iterrows()
                ]

        if not points:
            logger.warning("Scheduler: no KSE-100 data returned from any provider")
            return

        # 1. Update historical_prices
        params = {}
        value_clauses = []
        for i, p in enumerate(points):
            params[f"d{i}"] = p.date
            params[f"p{i}"] = p.close
            value_clauses.append(f"('KSE100', :d{i}, :p{i}, CAST('index' AS assettype))")

        db.execute(text(f"""
            INSERT INTO historical_prices (symbol, date, price, asset_type)
            VALUES {', '.join(value_clauses)}
            ON CONFLICT (symbol, date) DO UPDATE SET price = EXCLUDED.price
        """), params)
        
        # 2. Update history_psx (for technical indicators)
        for p in points:
            db.execute(text("""
                INSERT INTO history_psx (symbol, date, open, high, low, close, volume)
                VALUES ('KSE100', :date, :open, :high, :low, :close, :volume)
                ON CONFLICT (symbol, date) DO UPDATE SET
                    open=EXCLUDED.open, high=EXCLUDED.high, low=EXCLUDED.low, close=EXCLUDED.close, volume=EXCLUDED.volume
            """), {
                "date": p.date, "open": p.open, "high": p.high, "low": p.low, "close": p.close, "volume": p.volume
            })

        # 3. Update live_prices
        latest = points[-1]
        prev_close = points[-2].close if len(points) > 1 else latest.close
        change = latest.close - prev_close
        change_pct = (change / prev_close * 100) if prev_close != 0 else 0
        
        db.execute(text("""
            INSERT INTO live_prices (symbol, price, change, change_pct, open, high, low, volume, updated_at)
            VALUES ('KSE100', :price, :change, :change_pct, :open, :high, :low, :volume, :now)
            ON CONFLICT (symbol) DO UPDATE SET
                price=EXCLUDED.price, change=EXCLUDED.change, change_pct=EXCLUDED.change_pct,
                open=EXCLUDED.open, high=EXCLUDED.high, low=EXCLUDED.low, volume=EXCLUDED.volume,
                updated_at=EXCLUDED.updated_at
        """), {
            "price": latest.close, "change": change, "change_pct": change_pct,
            "open": latest.open, "high": latest.high, "low": latest.low,
            "volume": latest.volume, "now": datetime.now(timezone.utc) if 'timezone' in globals() else datetime.utcnow()
        })

        db.commit()
        logger.info(f"Scheduler: KSE-100 updated ({len(points)} points, latest={points[-1].date})")

        # --- Calculate Indicators for KSE100 ---
        try:
            import pandas as pd
            from database import engine as db_engine
            import math

            with db_engine.connect() as ind_conn:
                df = pd.read_sql(
                    text(
                        "SELECT id, date, close FROM history_psx "
                        "WHERE symbol = 'KSE100' ORDER BY date ASC LIMIT 300"
                    ),
                    ind_conn,
                )
                if len(df) >= 20:
                    df["sma_20"]     = df["close"].rolling(window=20).mean()
                    df["sma_50"]     = df["close"].rolling(window=50).mean()
                    df["sma_200"]    = df["close"].rolling(window=200).mean()
                    df["std_20"]     = df["close"].rolling(window=20).std()
                    df["bbu_20_2_0"] = df["sma_20"] + df["std_20"] * 2
                    df["bbl_20_2_0"] = df["sma_20"] - df["std_20"] * 2

                    delta = df["close"].diff()
                    gain  = delta.clip(lower=0).rolling(14).mean()
                    loss  = (-delta.clip(upper=0)).rolling(14).mean()
                    df["rsi_14"] = 100 - (100 / (1 + gain / loss.replace(0, float("nan"))))

                    latest_ind = df.iloc[-1]

                    def _safe(v):
                        return None if (v is None or (isinstance(v, float) and math.isnan(v))) else float(v)

                    ind_conn.execute(text("""
                        UPDATE history_psx SET
                            sma_20     = :s20,
                            sma_50     = :s50,
                            sma_200    = :s200,
                            bbu_20_2_0 = :bbu,
                            bbl_20_2_0 = :bbl,
                            rsi_14     = :rsi
                        WHERE id = :id
                    """), {
                        "s20":  _safe(latest_ind["sma_20"]),
                        "s50":  _safe(latest_ind["sma_50"]),
                        "s200": _safe(latest_ind["sma_200"]),
                        "bbu":  _safe(latest_ind["bbu_20_2_0"]),
                        "bbl":  _safe(latest_ind["bbl_20_2_0"]),
                        "rsi":  _safe(latest_ind["rsi_14"]),
                        "id":   int(latest_ind["id"]),
                    })
                    ind_conn.commit()
            logger.info("Scheduler: KSE-100 indicators updated")
        except Exception as e:
            logger.error(f"Scheduler: KSE-100 indicator calculation failed: {e}")

    except Exception as e:
        logger.error(f"Scheduler: KSE-100 refresh failed: {e}")
        db.rollback()
    finally:
        db.close()


def job_nightly_mf_navs():
    """Nightly job: fetch mutual fund NAVs from Sarmaaya and save to live_prices."""
    logger.info("Scheduler: fetching mutual fund NAVs...")
    from database import SessionLocal
    from data_providers.sarmaaya_scraper import SarmaayaScraper
    from sqlalchemy import text

    scraper = SarmaayaScraper()
    try:
        mf_symbols = scraper.get_all_symbols()
        if not mf_symbols:
            logger.warning("Scheduler: no MF symbols returned")
            return
    except Exception as e:
        logger.error(f"Scheduler: MF NAV fetch failed to get symbols: {e}")
        return

    db = SessionLocal()
    saved = 0
    try:
        rows = []
        for sym_info in mf_symbols:
            sym = sym_info.symbol.upper()
            q = scraper.get_quote(sym)
            if q and q.price is not None:
                rows.append((sym, q.price, q.change, q.change_pct))

        # Chunk into batches of 20 rows to stay under Supabase's statement timeout
        CHUNK = 20
        for i in range(0, len(rows), CHUNK):
            chunk = rows[i:i + CHUNK]
            params = {"now": datetime.utcnow()}
            value_clauses = []
            for j, (sym, price, change, change_pct) in enumerate(chunk):
                params[f"s{j}"]  = sym
                params[f"p{j}"]  = price
                params[f"c{j}"]  = change
                params[f"cp{j}"] = change_pct
                value_clauses.append(f"(:s{j}, :p{j}, :c{j}, :cp{j}, :now)")
            try:
                db.execute(text(f"""
                    INSERT INTO live_prices (symbol, price, change, change_pct, updated_at)
                    VALUES {', '.join(value_clauses)}
                    ON CONFLICT (symbol) DO UPDATE SET
                        price      = EXCLUDED.price,
                        change     = EXCLUDED.change,
                        change_pct = EXCLUDED.change_pct,
                        updated_at = :now
                """), params)

                # Save to history_psx too for graphing
                today_str = date.today().isoformat()
                hist_params = {"today": today_str}
                hist_clauses = []
                for j, (sym, price, _, _) in enumerate(chunk):
                    hist_params[f"s{j}"] = sym
                    hist_params[f"p{j}"] = price
                    hist_clauses.append(f"(:s{j}, :today, :p{j})")
                db.execute(text(f"""
                    INSERT INTO history_psx (symbol, date, close)
                    VALUES {', '.join(hist_clauses)}
                    ON CONFLICT (symbol, date) DO UPDATE SET
                        close = EXCLUDED.close
                """), hist_params)

                db.commit()
                saved += len(chunk)
            except Exception as chunk_err:
                logger.warning(f"Scheduler: MF NAV chunk failed (skipping): {chunk_err}")
                db.rollback()


        logger.info(f"Scheduler: MF NAVs updated ({saved} funds)")
    except Exception as e:
        logger.error(f"Scheduler: MF NAV update failed: {e}")
        db.rollback()
    finally:
        db.close()


# ── Scheduler setup ────────────────────────────────────────────────────────────

_scheduler: BackgroundScheduler = None


def start_scheduler():
    """Initialize and start all APScheduler jobs. Call once from FastAPI startup."""
    global _scheduler

    if _scheduler and _scheduler.running:
        return

    _scheduler = BackgroundScheduler(timezone=PKT)

    # Every 10 minutes during market hours (the job itself checks if market is open)
    _scheduler.add_job(
        job_refresh_live_prices,
        trigger=CronTrigger(
            day_of_week="mon-fri",
            hour="9-15",
            minute="*/10",
            timezone=PKT,
        ),
        id="live_prices",
        name="Refresh live equity prices",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=120,
    )

    # Nightly at 02:00 PKT — EOD historical append
    _scheduler.add_job(
        job_nightly_eod,
        trigger=CronTrigger(hour=2, minute=0, timezone=PKT),
        id="nightly_eod",
        name="Nightly EOD historical prices",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=3600,
    )

    # Every 10 minutes during market hours — KSE-100 index value
    _scheduler.add_job(
        job_refresh_kse100,
        trigger=CronTrigger(
            day_of_week="mon-fri",
            hour="9-15",
            minute="*/10",
            timezone=PKT,
        ),
        id="kse100",
        name="Refresh KSE-100 index",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=120,
    )

    # Nightly at 02:15 PKT — MF NAVs (after EOD finishes)
    _scheduler.add_job(
        job_nightly_mf_navs,
        trigger=CronTrigger(hour=2, minute=15, timezone=PKT),
        id="nightly_mf_navs",
        name="Nightly mutual fund NAVs",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=3600,
    )

    _scheduler.start()
    logger.info(
        "Scheduler started — jobs: live_prices + kse100 (every 10min market hours Mon-Fri), "
        "nightly_eod (02:00 PKT, includes change recalc), nightly_mf_navs (02:15 PKT)"
    )


def stop_scheduler():
    """Gracefully stop the scheduler. Call from FastAPI shutdown."""
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
