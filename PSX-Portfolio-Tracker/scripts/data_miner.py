import os
import time
import logging
from datetime import datetime, timedelta
from typing import List

# Setup path for imports
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../backend'))

from sqlalchemy.orm import Session
from database import SessionLocal, create_tables
from models import AssetType
import crud

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

PROGRESS_FILE = os.path.join(os.path.dirname(__file__), "miner_progress.txt")

def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r") as f:
            return set(f.read().splitlines())
    return set()

def save_progress(symbol):
    with open(PROGRESS_FILE, "a") as f:
        f.write(f"{symbol}\n")

def run_miner(days=7):
    """ Proactively fetches history for ALL active PSX symbols. """
    logger.info(f"Starting PSX Data Miner (Range: {days} days)...")
    
    # Ensure tables exist
    create_tables()
    
    db = SessionLocal()
    from data_providers.composite_provider import CompositeProvider
    provider = CompositeProvider()
    
    synced_symbols = load_progress()
    
    try:
        # 1. Get all active symbols
        logger.info("Fetching active symbol list...")
        all_stocks = provider.get_all_symbols()
        if not all_stocks:
            logger.error("Could not fetch symbols. API might be down.")
            return

        to_sync = [s for s in all_stocks if s.symbol not in synced_symbols]
        logger.info(f"Found {len(all_stocks)} symbols total. {len(to_sync)} remaining to sync.")
        
        # 2. Sync history for each symbol
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        success_count = 0
        try:
            for i, stock in enumerate(to_sync):
                symbol = stock.symbol
                logger.info(f"[{i+1}/{len(to_sync)}] Syncing {symbol} ({stock.asset_type})...")
                
                try:
                    # 1. Fetch current quote to get sector and latest price
                    quote = provider.get_quote(symbol)
                    if quote and quote.price is not None:
                        # Update GlobalSymbol with sector and name
                        if quote.sector_name:
                            stock.sector = quote.sector_name
                        crud.save_global_symbols(db, [stock])
                        
                        # Save live price
                        crud.save_live_prices(db, {symbol: quote})

                    # 2. Fetch history
                    history = provider.get_historical(symbol, start_date, end_date)
                    if history:
                        to_save = [{"date": p.date, "price": p.close} for p in history]
                        crud.save_historical_prices(db, symbol, to_save, stock.asset_type)
                        logger.info(f"  Successfully synced {symbol} ({len(to_save)} points)")
                        success_count += 1
                        save_progress(symbol)
                    else:
                        logger.warning(f"  No history found for {symbol}")
                    
                    # Respectful Rate Limiting
                    time.sleep(0.5)
                    
                except Exception as e:
                    logger.error(f"Failed to sync {symbol}: {e}")
                    db.rollback()
                    continue
        except KeyboardInterrupt:
            logger.info("Sync interrupted by user. Progress saved.")

        logger.info(f"Miner finished! Successfully synced {success_count} symbols.")

        # 3. Always sync KSE-100 benchmark index history
        logger.info("Syncing KSE-100 benchmark history...")
        try:
            bench_history = provider.get_historical("KSE100", start_date, end_date)
            if bench_history:
                to_save = [{"date": p.date, "price": p.close} for p in bench_history]
                crud.save_historical_prices(db, "KSE100", to_save, AssetType.STOCK)
                logger.info(f"  KSE-100 synced ({len(to_save)} points)")
            else:
                logger.warning("  No KSE-100 history returned")
        except Exception as e:
            logger.error(f"Failed to sync KSE-100: {e}")

    finally:
        db.close()

if __name__ == "__main__":
    days_to_sync = 7
    if len(sys.argv) > 1:
        try:
            # Support specifying days (e.g. 3650 for 10 years)
            days_to_sync = int(sys.argv[1])
        except ValueError:
            pass
    run_miner(days_to_sync)
