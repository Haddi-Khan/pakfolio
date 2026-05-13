import sys
import os
# Add the current directory to sys.path so we can import data_providers
sys.path.append(os.getcwd())

from data_providers.psx_scraper import _fetch_psx_history, _fetch_yf_history, _calculate_technical_indicators, _get_robust_session
from database import SessionLocal
from models import HistoryPSX, GlobalSymbol
from sqlalchemy.dialects.postgresql import insert as pg_insert
import pandas as pd
import time
import random
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("targeted_scrape")

# Use the pre-configured engine from database.py which has all the SSL and URL fixes
from database import engine

def get_scraper_db():
    from sqlalchemy.orm import sessionmaker
    # Still use a fresh session to avoid stale state
    Session = sessionmaker(bind=engine)
    return Session()

def clean(val):
    return None if pd.isna(val) else val

def scrape_missing():
    # Retry initialization up to 10 times
    targets = []
    init_success = False
    init_retries = 0
    while not init_success and init_retries < 10:
        db = get_scraper_db()
        from sqlalchemy import func
        try:
            all_stocks = db.query(GlobalSymbol).filter(GlobalSymbol.asset_type == 'stock').all()
            existing = {r[0] for r in db.query(HistoryPSX.symbol).distinct().all()}
            missing_zero = [s for s in all_stocks if s.symbol not in existing]
            short_history = db.query(HistoryPSX.symbol).group_by(HistoryPSX.symbol).having(func.count(HistoryPSX.id) < 200).all()
            short_symbols = {r[0] for r in short_history}
            missing_short = [s for s in all_stocks if s.symbol in short_symbols]
            missing = missing_zero + missing_short
            jsclr1 = db.query(GlobalSymbol).filter(GlobalSymbol.symbol == 'JSCLR1').first()
            if jsclr1:
                missing = [m for m in missing if m.symbol != 'JSCLR1']
                missing.insert(0, jsclr1)
            targets = [{"symbol": s.symbol, "name": s.name} for s in missing]
            init_success = True
        except Exception as e:
            init_retries += 1
            logger.error(f"Initialization attempt {init_retries} failed: {e}")
            
            # Fallback to local text file if DB is down
            if os.path.exists("psx_quotes.txt") and not targets:
                logger.info("Database down. Attempting to load symbols from psx_quotes.txt fallback...")
                try:
                    with open("psx_quotes.txt", "r") as f:
                        lines = f.readlines()
                        # Simple parse: assuming lines start with symbol
                        fallback_syms = []
                        for line in lines[:500]: # limit to first 500
                            parts = line.split()
                            if parts: fallback_syms.append(parts[0])
                        targets = [{"symbol": s, "name": s} for s in fallback_syms]
                        logger.info(f"Loaded {len(targets)} symbols from text file.")
                except: pass

            logger.info("Waiting 15s to retry database...")
            time.sleep(15)
        finally:
            db.close()

    if not targets:
        logger.info("No targets found to scrape.")
        return

    logger.info(f"Found {len(targets)} targets. Starting...")

    session = _get_robust_session()
    
    for i, target in enumerate(targets):
        symbol = target["symbol"]
        name = target["name"]
        logger.info(f"[{i+1}/{len(targets)}] Scraping {symbol}...")
        
        success = False
        retries = 0
        while not success and retries < 3:
            db = get_scraper_db()
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
                    logger.warning(f"No data found for {symbol}")
                    success = True
                    continue

                df_combined = _calculate_technical_indicators(df_combined)
                
                objects_to_add = []
                for row in df_combined.to_dict('records'):
                    dt = row['Date'].to_pydatetime().date()
                    objects_to_add.append({
                        "symbol": symbol, "symbol_name": name, "date": dt,
                        "open": clean(row.get('Open')), "high": clean(row.get('High')),
                        "low": clean(row.get('Low')), "close": clean(row.get('Close')),
                        "volume": clean(row.get('Volume')), "sma_50": clean(row.get('SMA_50')),
                        "sma_200": clean(row.get('SMA_200')), "sma_20": clean(row.get('SMA_20')),
                        "std_20": clean(row.get('STD_20')), "bbl_20_2_0": clean(row.get('BBL_20_2.0')),
                        "bbu_20_2_0": clean(row.get('BBU_20_2.0')), "rsi_14": clean(row.get('RSI_14'))
                    })

                if objects_to_add:
                    stmt = pg_insert(HistoryPSX).values(objects_to_add)
                    update_dict = {k: stmt.excluded[k] for k in objects_to_add[0].keys() if k not in ['symbol', 'date']}
                    stmt = stmt.on_conflict_do_update(index_elements=['symbol', 'date'], set_=update_dict)
                    db.execute(stmt)
                    db.commit()
                    logger.info(f"Saved {len(objects_to_add)} rows for {symbol}")
                
                success = True
                time.sleep(random.uniform(1.0, 2.0))
                
            except Exception as e:
                retries += 1
                logger.error(f"Attempt {retries} failed for {symbol}: {e}")
                db.rollback()
                time.sleep(5)
            finally:
                db.close()

if __name__ == "__main__":
    scrape_missing()
