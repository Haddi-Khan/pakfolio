"""
Backfill historical_prices for symbols missing from the table.

Fetches up to 10 years of EOD data from dps.psx.com.pk/timeseries/eod/{SYMBOL}
for any GlobalSymbol that has no rows in historical_prices.

Skips isDebt=true symbols (TFCs/bonds — no meaningful price history).

Run: python scripts/backfill_history.py
"""
import os, sys, logging, time
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../backend'))

from database import SessionLocal, create_tables
from models import GlobalSymbol, HistoricalPrice
from sqlalchemy import text

import httpx

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

PSX_BASE = "https://dps.psx.com.pk"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; PSXTracker/1.0)", "Accept": "application/json"}
FROM_DATE = (date.today() - timedelta(days=365 * 10)).isoformat()
TO_DATE   = date.today().isoformat()
DELAY     = 0.3   # seconds between requests to avoid rate-limiting
BATCH_DB  = 500   # rows per DB commit


def _ts_to_date(ts):
    try:
        ts = int(ts)
        if ts > 1e10:
            ts //= 1000
        from datetime import datetime
        return datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d")
    except Exception:
        return None


def fetch_history(symbol: str, client: httpx.Client):
    """Fetch EOD history for one symbol. Returns list of (date, close) tuples."""
    try:
        r = client.get(
            f"{PSX_BASE}/timeseries/eod/{symbol}",
            params={"from": FROM_DATE, "to": TO_DATE},
            timeout=20,
        )
        if r.status_code != 200:
            return []
        data = r.json()
        rows_data = data.get("data", data) if isinstance(data, dict) else data
        rows = []
        for row in rows_data:
            if isinstance(row, list) and len(row) >= 2:
                dt = _ts_to_date(row[0])
                close = row[1]  # [timestamp, close, volume, open] shape
                if dt and close:
                    rows.append((dt, float(close)))
        return rows
    except Exception as e:
        logger.debug(f"  {symbol}: fetch error — {e}")
        return []


def run():
    create_tables()
    db = SessionLocal()

    try:
        # Find symbols missing from historical_prices
        existing_syms = {
            r[0] for r in db.execute(text(
                "SELECT DISTINCT symbol FROM historical_prices"
            )).fetchall()
        }

        # Get debt symbols to skip
        debt_sectors = {"BILLS AND BONDS"}
        all_gs = db.query(GlobalSymbol).all()
        missing = [
            gs.symbol for gs in all_gs
            if gs.symbol not in existing_syms
            and gs.sector not in debt_sectors
        ]

        logger.info(f"Symbols already in historical_prices: {len(existing_syms)}")
        logger.info(f"Symbols to backfill: {len(missing)}")

        total_rows = 0
        failed = []

        with httpx.Client(headers=HEADERS, timeout=20, follow_redirects=True) as client:
            for i, sym in enumerate(missing, 1):
                rows = fetch_history(sym, client)
                if not rows:
                    failed.append(sym)
                    if i % 50 == 0:
                        logger.info(f"  [{i}/{len(missing)}] {total_rows} rows saved so far, {len(failed)} no-data")
                    time.sleep(DELAY)
                    continue

                # Batch upsert
                CHUNK = BATCH_DB
                for j in range(0, len(rows), CHUNK):
                    chunk = rows[j:j + CHUNK]
                    params = {}
                    value_clauses = []
                    for k, (dt, close) in enumerate(chunk):
                        params[f"s{k}"] = sym
                        params[f"d{k}"] = dt
                        params[f"p{k}"] = close
                        value_clauses.append(f"(:s{k}, :d{k}, :p{k}, CAST('STOCK' AS assettype))")
                    db.execute(text(f"""
                        INSERT INTO historical_prices (symbol, date, price, asset_type)
                        VALUES {', '.join(value_clauses)}
                        ON CONFLICT (symbol, date) DO NOTHING
                    """), params)
                db.commit()
                total_rows += len(rows)

                if i % 50 == 0 or i == len(missing):
                    logger.info(f"  [{i}/{len(missing)}] {sym}: {len(rows)} rows | total saved: {total_rows}")

                time.sleep(DELAY)

        logger.info(f"\nBackfill complete: {total_rows} rows added for {len(missing) - len(failed)} symbols")
        logger.info(f"No data (skipped): {len(failed)} symbols — {failed[:20]}")

        # Final summary
        hist_count = db.execute(text("SELECT COUNT(DISTINCT symbol) FROM historical_prices")).scalar()
        logger.info(f"historical_prices now covers {hist_count} symbols")

    except Exception as e:
        logger.error(f"Backfill failed: {e}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run()
