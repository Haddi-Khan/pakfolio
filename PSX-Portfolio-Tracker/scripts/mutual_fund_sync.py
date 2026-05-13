import os
import time
import logging
from datetime import datetime, timedelta
import sys

# Setup path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '../backend'))

from database import SessionLocal, create_tables
from data_providers.sarmaaya_scraper import SarmaayaScraper
from models import AssetType
import crud

logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("mf_sync.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

PROGRESS_FILE = "mf_sync_progress.txt"

def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r") as f:
            return set(f.read().splitlines())
    return set()

def save_progress(symbol):
    with open(PROGRESS_FILE, "a") as f:
        f.write(f"{symbol}\n")

def run_mf_sync(years=5):
    logger.info(f"Starting Bulk Mutual Fund Sync ({years} years)...")
    
    create_tables()
    db = SessionLocal()
    scraper = SarmaayaScraper()
    
    # 1. Get all known mutual funds
    logger.info("Fetching mutual fund list...")
    scraper._ensure_cache()
    funds = scraper.get_all_symbols()
    if not funds:
        logger.error("Could not fetch mutual funds.")
        return

    # Filter out already synced
    synced = load_progress()
    to_sync = [f for f in funds if f.symbol not in synced]
    
    logger.info(f"Total funds: {len(funds)}. Remaining: {len(to_sync)}")

    # 2. Sync history
    # 5 years = ~1825 days
    days = years * 365
    
    success_count = 0
    try:
        for i, fund in enumerate(to_sync):
            symbol = fund.symbol
            logger.info(f"[{i+1}/{len(to_sync)}] Syncing fund: {symbol}...")
            
            try:
                # Use a dummy from_date to trigger the 'days' calculation in scraper
                # The scraper uses days = (now - from_date).days + 2
                # Note: 'days=3650' fetches approx 10 years of data.
                # The scraper's get_historical method internally constructs the URL.
                # The 'days' variable here controls the 'from_date' passed to the scraper.
                from_date = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
                to_date = datetime.utcnow().strftime("%Y-%m-%d")
                
                history = scraper.get_historical(symbol, from_date, to_date)
                
                if history:
                    to_save = [{"date": p.date, "price": p.close} for p in history]
                    crud.save_historical_prices(db, symbol, to_save, AssetType.MUTUAL_FUND)
                    success_count += 1
                    save_progress(symbol)
                    logger.info(f"  Saved {len(history)} NAV points for {symbol}")
                else:
                    logger.warning(f"  No history found for {symbol}")
                
                # Jitter already in scraper, but let's be careful here too
                time.sleep(0.5)
                
            except Exception as e:
                db.rollback()
                logger.error(f"Failed to sync {symbol}: {e}")
                # Re-check database connectivity if needed
                continue

    except KeyboardInterrupt:
        logger.info("Sync interrupted. Progress saved.")
    finally:
        db.close()
        logger.info(f"MF sync finished! Synced {success_count} NEW funds.")

if __name__ == "__main__":
    years_to_sync = 10
    if len(sys.argv) > 1:
        try:
            years_to_sync = int(sys.argv[1])
        except ValueError:
            pass
    run_mf_sync(years_to_sync)
