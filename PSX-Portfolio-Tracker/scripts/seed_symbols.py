"""
Fast seeder using dps.psx.com.pk:

  Phase 1: GET /symbols  → batch-upsert all 1026 GlobalSymbol rows (names + sectors)
  Phase 2: Concurrent HTML scrape per equity symbol → batch-upsert LivePrice rows

  Skips isDebt=true symbols for live prices (TFCs, PIBs, T-Bills have no exchange price).

Run: python scripts/seed_symbols.py
"""
import os, sys, re, logging
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../backend'))

from database import SessionLocal, create_tables
from models import GlobalSymbol, LivePrice
from sqlalchemy import text

import httpx

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BASE = "https://dps.psx.com.pk"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; PSXTracker/1.0)",
    "Accept": "application/json, text/html",
}
MAX_WORKERS = 10   # concurrent HTTP connections for price scraping
BATCH_DB    = 100  # rows per DB batch insert


def _to_float(v):
    try:
        return float(str(v).replace(",", "")) if v is not None and v != "" else None
    except (TypeError, ValueError):
        return None


def fetch_symbols():
    """GET /symbols — returns all listed symbols with name, sectorName, isETF, isDebt."""
    logger.info("Fetching symbol list from PSX /symbols ...")
    with httpx.Client(headers=HEADERS, timeout=20, follow_redirects=True) as c:
        r = c.get(f"{BASE}/symbols")
        r.raise_for_status()
        data = r.json()
    logger.info(f"  {len(data)} symbols fetched")
    return data


def scrape_price(symbol: str, client: httpx.Client):
    """Scrape latest close price from the company HTML page."""
    try:
        r = client.get(f"{BASE}/company/{symbol}", timeout=12)
        if r.status_code != 200:
            return symbol, None
        html = r.text
        m = re.search(r'quote__close[^>]*>[^<]*Rs\.?\s*([\d,]+\.?\d*)', html)
        price = _to_float(m.group(1)) if m else None
        return symbol, price
    except Exception:
        return symbol, None


def batch_upsert_symbols(db, rows):
    """Batch upsert GlobalSymbol rows. rows = list of (symbol, name, sector, at_val)."""
    if not rows:
        return
    params = {}
    value_clauses = []
    for i, (sym, name, sector, at_val) in enumerate(rows):
        params[f"s{i}"] = sym
        params[f"n{i}"] = name
        params[f"sec{i}"] = sector
        params[f"at{i}"] = at_val
        value_clauses.append(
            f"(:s{i}, :n{i}, :sec{i}, CAST(:at{i} AS assettype), NOW())"
        )
    db.execute(text(f"""
        INSERT INTO global_symbols (symbol, name, sector, asset_type, updated_at)
        VALUES {', '.join(value_clauses)}
        ON CONFLICT (symbol) DO UPDATE SET
            name   = COALESCE(EXCLUDED.name,   global_symbols.name),
            sector = COALESCE(EXCLUDED.sector, global_symbols.sector),
            updated_at = NOW()
    """), params)


def batch_upsert_prices(db, rows):
    """Batch upsert LivePrice rows. rows = list of (symbol, price)."""
    if not rows:
        return
    params = {}
    value_clauses = []
    for i, (sym, price) in enumerate(rows):
        params[f"s{i}"] = sym
        params[f"p{i}"] = price
        value_clauses.append(f"(:s{i}, :p{i}, NOW())")
    db.execute(text(f"""
        INSERT INTO live_prices (symbol, price, updated_at)
        VALUES {', '.join(value_clauses)}
        ON CONFLICT (symbol) DO UPDATE SET
            price      = EXCLUDED.price,
            updated_at = NOW()
    """), params)


def run():
    create_tables()
    db = SessionLocal()

    try:
        symbols = fetch_symbols()

        # ── Phase 1: Batch upsert GlobalSymbols ───────────────────────────────
        equity_symbols = []
        gs_rows = []
        for item in symbols:
            sym = (item.get("symbol") or "").strip().upper()
            if not sym:
                continue
            name    = item.get("name") or None
            sector  = item.get("sectorName") or None
            is_debt = item.get("isDebt", False)

            gs_rows.append((sym, name, sector, "STOCK"))
            if not is_debt:
                equity_symbols.append(sym)

        # Insert in chunks of BATCH_DB
        for i in range(0, len(gs_rows), BATCH_DB):
            batch_upsert_symbols(db, gs_rows[i:i + BATCH_DB])
        db.commit()
        logger.info(f"GlobalSymbol: {len(gs_rows)} rows upserted, {len(equity_symbols)} equity symbols to price")

        # ── Phase 2: Concurrent price scraping ────────────────────────────────
        logger.info(f"Fetching live prices with {MAX_WORKERS} workers ...")
        saved = 0
        errors = 0
        price_rows = []

        with httpx.Client(headers=HEADERS, timeout=12, follow_redirects=True) as client:
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
                futures = {pool.submit(scrape_price, sym, client): sym for sym in equity_symbols}
                for i, future in enumerate(as_completed(futures), 1):
                    sym, price = future.result()
                    if price is not None:
                        price_rows.append((sym, price))
                    else:
                        errors += 1

                    if len(price_rows) >= BATCH_DB:
                        batch_upsert_prices(db, price_rows)
                        db.commit()
                        saved += len(price_rows)
                        price_rows = []
                        logger.info(f"  [{i}/{len(equity_symbols)}] {saved} prices saved, {errors} no-price")

        # Final flush
        if price_rows:
            batch_upsert_prices(db, price_rows)
            db.commit()
            saved += len(price_rows)

        logger.info(f"\nLivePrice: {saved} saved, {errors} had no price")

        # ── Summary ────────────────────────────────────────────────────────────
        total_gs    = db.query(GlobalSymbol).count()
        with_sector = db.query(GlobalSymbol).filter(GlobalSymbol.sector != None).count()
        total_lp    = db.query(LivePrice).count()
        logger.info(
            f"DB: {total_gs} global symbols ({with_sector} with sector), {total_lp} live prices"
        )

    except Exception as e:
        logger.error(f"Seeder failed: {e}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run()
