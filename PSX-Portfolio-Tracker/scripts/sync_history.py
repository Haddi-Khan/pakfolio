import sys
import os
import time
from datetime import date, timedelta, datetime

# Add the backend directory to the path so we can import models and crud
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from database import SessionLocal, create_tables
from models import HistoricalPrice, Trade, AssetType
from data_providers import active_provider
import crud

def sync_all_history(days=365):
    db = SessionLocal()
    try:
        # 1. Ensure table exists
        create_tables()
        
        # 2. Find all unique symbols in the system
        trades = db.query(Trade.symbol, Trade.asset_type).distinct().all()
        symbols = [(t.symbol.upper(), t.asset_type) for t in trades]
        
        if not symbols:
            print("No symbols found in trades table. Nothing to sync.")
            return

        print(f"Found {len(symbols)} symbols to sync history for...")
        
        to_date = date.today()
        from_date = (to_date - timedelta(days=days))
        
        for symbol, asset_type in symbols:
            print(f"Syncing {symbol} ({asset_type.value})...")
            
            # Use our persistence logic by just calling the existing API 
            # (which we just updated in main.py to handle DB check/save)
            # Actually, main.py is the API layer. We should use the raw logic here.
            
            # Check DB count
            count = db.query(HistoricalPrice).filter(
                HistoricalPrice.symbol == symbol,
                HistoricalPrice.date >= from_date
            ).count()
            
            if count > (days * 0.8): # Arbitrary 80% coverage check
                print(f"  Existing data seems sufficient ({count} points). Skipping API call.")
                continue

            print(f"  Fetching from API ({from_date.isoformat()} to {to_date.isoformat()})...")
            try:
                points = active_provider.get_historical(symbol, from_date.isoformat(), to_date.isoformat())
                if points:
                    print(f"  Saving {len(points)} points to DB...")
                    to_save = [{"date": p.date, "price": p.close} for p in points]
                    crud.save_historical_prices(db, symbol, to_save, asset_type)
                    print("  Success.")
                else:
                    print("  No data returned from API.")
            except Exception as e:
                print(f"  Error syncing {symbol}: {e}")
            
            # Be nice to the API
            time.sleep(1)

        print("\nSync completed successfully.")
        
    finally:
        db.close()

if __name__ == "__main__":
    # Sync last 1 year by default
    sync_all_history(days=365)
