import os
import time
import logging
from datetime import datetime, timedelta
import sys

# Setup path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '../backend'))

from database import SessionLocal, create_tables
from data_providers.sarmaaya_provider import SarmaayaProvider
from models import AssetType
import crud

logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bulk_sync.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

PROGRESS_FILE = "sync_progress.txt"

def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r") as f:
            return set(f.read().splitlines())
    return set()

def save_progress(symbol):
    with open(PROGRESS_FILE, "a") as f:
        f.write(f"{symbol}\n")

def run_bulk_sync(years=5):
    logger.info(f"Starting Bulk PSX Data Sync ({years} years)...")
    
    create_tables()
    db = SessionLocal()
    provider = SarmaayaProvider()
    
    # 1. Get all active symbols
    logger.info("Fetching symbol list...")
    stocks = provider.get_all_symbols()
    if not stocks:
        logger.error("Could not fetch symbols.")
        return

    # Convert SymbolInfo objects to a list of dicts that the rest of the script expects
    all_stocks = [{"symbol": s.symbol, "name": s.name} for s in stocks]

    # Filter out already synced symbols if resuming
    synced_symbols = load_progress()
    to_sync = [s for s in all_stocks if s['symbol'] not in synced_symbols]
    
    logger.info(f"Total symbols: {len(all_stocks)}. Remaining to sync: {len(to_sync)}")

    # 2. Date range
    logger.info(f"Connecting to Sarmaaya API to fetch 10-year history for {len(all_stocks)} active symbols...")
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=3650)).strftime("%Y-%m-%d") # Changed timedelta to 3650
    
    success_count = 0
    try:
        for i, stock in enumerate(to_sync):
            symbol = stock['symbol']
            logger.info(f"[{i+1}/{len(to_sync)}] Syncing {symbol} from {start_date}...")
            
            try:
                history = provider.get_historical(symbol, start_date, end_date)
                if history:
                    to_save = [{"date": p.date, "price": p.close} for p in history]
                    crud.save_historical_prices(db, symbol, to_save, AssetType.STOCK)
                    success_count += 1
                    save_progress(symbol)
                    logger.info(f"  Saved {len(history)} data points for {symbol}")
                else:
                    logger.warning(f"  No history found for {symbol}")
                
                # Rate Limiting: 0.7s to be extra safe for bulk
                time.sleep(0.7)
                
            except Exception as e:
                logger.error(f"Failed to sync {symbol}: {e}")
                continue

    except KeyboardInterrupt:
        logger.info("Sync interrupted by user. Progress saved.")
    finally:
        db.close()
        logger.info(f"Bulk sync finished! Synced {success_count} NEW symbols.")

if __name__ == "__main__":
    # Get years from command line if provided
    years_to_sync = 5
    if len(sys.argv) > 1:
        try:
            years_to_sync = int(sys.argv[1])
        except ValueError:
            pass
            
    run_bulk_sync(years_to_sync)
