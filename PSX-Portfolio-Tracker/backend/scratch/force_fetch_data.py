
import os
import logging
import time
from datetime import datetime, timezone
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool
from sqlalchemy.dialects.postgresql import insert as pg_insert
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("force_fetch")

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///./psx_portfolio.db"

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Using NullPool and disabling prepared statements for stability
engine = create_engine(
    DATABASE_URL, 
    poolclass=NullPool,
    connect_args={"prepare_threshold": None, "connect_timeout": 60}
)

def force_sync_symbols():
    logger.info("Force syncing symbols from PSX (CHUNKED MODE)...")
    try:
        import sys
        sys.path.append(".")
        from data_providers.psx_scraper import PSXScraper
        from models import GlobalSymbol, LivePrice
        
        scraper = PSXScraper()
        symbols = scraper.get_all_symbols()
        logger.info(f"Fetched {len(symbols)} symbols from PSX.")
        
        if not symbols:
            return
            
        now = datetime.now(timezone.utc)
        CHUNK_SIZE = 50 # Small chunks for pooler stability
        
        # 1. Chunked Update global_symbols
        logger.info("Updating global_symbols in chunks...")
        symbol_data = [
            {"symbol": s.symbol.upper(), "name": s.name, "asset_type": s.asset_type, "updated_at": now}
            for s in symbols
        ]
        
        for i in range(0, len(symbol_data), CHUNK_SIZE):
            chunk = symbol_data[i:i + CHUNK_SIZE]
            with engine.connect() as conn:
                stmt = pg_insert(GlobalSymbol).values(chunk)
                stmt = stmt.on_conflict_do_update(
                    index_elements=['symbol'],
                    set_={"name": stmt.excluded.name, "asset_type": stmt.excluded.asset_type, "updated_at": stmt.excluded.updated_at}
                )
                conn.execute(stmt)
                conn.commit()
            logger.info(f"Symbols chunk {i//CHUNK_SIZE + 1} done.")

        # 2. Chunked Update live_prices
        logger.info("Fetching bulk quotes...")
        quotes = scraper.get_quotes_bulk([s.symbol for s in symbols])
        
        if quotes:
            logger.info(f"Fetched {len(quotes)} quotes. Updating live_prices in chunks...")
            quote_data = []
            for sym, q in quotes.items():
                if q.price is None: continue
                quote_data.append({
                    "symbol": sym.upper(), "price": q.price, "change": q.change, "change_pct": q.change_pct,
                    "open": q.open, "high": q.high, "low": q.low, "volume": q.volume, "prev_close": q.prev_close, "updated_at": now
                })
            
            for i in range(0, len(quote_data), CHUNK_SIZE):
                chunk = quote_data[i:i + CHUNK_SIZE]
                with engine.connect() as conn:
                    stmt = pg_insert(LivePrice).values(chunk)
                    stmt = stmt.on_conflict_do_update(
                        index_elements=['symbol'],
                        set_={
                            "price": stmt.excluded.price, "change": stmt.excluded.change, "change_pct": stmt.excluded.change_pct,
                            "open": stmt.excluded.open, "high": stmt.excluded.high, "low": stmt.excluded.low, 
                            "volume": stmt.excluded.volume, "prev_close": stmt.excluded.prev_close, "updated_at": stmt.excluded.updated_at
                        }
                    )
                    conn.execute(stmt)
                    conn.commit()
                logger.info(f"Prices chunk {i//CHUNK_SIZE + 1} done.")
                
        logger.info("FORCE SYNC COMPLETE!")
                
    except Exception as e:
        logger.error(f"Force sync failed: {e}")

if __name__ == "__main__":
    force_sync_symbols()
