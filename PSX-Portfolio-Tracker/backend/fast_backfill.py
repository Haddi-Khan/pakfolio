import pandas as pd
import numpy as np
from database import SessionLocal
from models import HistoryPSX
from sqlalchemy import text
import logging
from concurrent.futures import ThreadPoolExecutor
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fast_backfill")

def calculate_indicators(df):
    df = df.sort_values('date')
    # SMA
    df['sma_20'] = df['close'].rolling(window=20).mean()
    df['sma_50'] = df['close'].rolling(window=50).mean()
    df['sma_200'] = df['close'].rolling(window=200).mean()
    # Bollinger
    df['std_20'] = df['close'].rolling(window=20).std()
    df['bbu_20_2_0'] = df['sma_20'] + (df['std_20'] * 2)
    df['bbl_20_2_0'] = df['sma_20'] - (df['std_20'] * 2)
    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi_14'] = 100 - (100 / (1 + rs))
    return df

def process_symbol(symbol):
    db = SessionLocal()
    try:
        query = db.query(HistoryPSX).filter(HistoryPSX.symbol == symbol).order_by(HistoryPSX.date.asc())
        df = pd.read_sql(query.statement, db.bind)
        if df.empty or len(df) < 20:
            return
        
        df = calculate_indicators(df)
        
        # Batch update
        update_data = []
        for _, row in df.iterrows():
            if pd.isna(row['sma_20']): continue
            update_data.append({
                'id': int(row['id']),
                's20': float(row['sma_20']) if not pd.isna(row['sma_20']) else None,
                's50': float(row['sma_50']) if not pd.isna(row['sma_50']) else None,
                's200': float(row['sma_200']) if not pd.isna(row['sma_200']) else None,
                'bbu': float(row['bbu_20_2_0']) if not pd.isna(row['bbu_20_2_0']) else None,
                'bbl': float(row['bbl_20_2_0']) if not pd.isna(row['bbl_20_2_0']) else None,
                'rsi': float(row['rsi_14']) if not pd.isna(row['rsi_14']) else None
            })
        
        if update_data:
            stmt = text("""
                UPDATE history_psx 
                SET sma_20=:s20, sma_50=:s50, sma_200=:s200, 
                    bbu_20_2_0=:bbu, bbl_20_2_0=:bbl, rsi_14=:rsi
                WHERE id=:id
            """)
            # Process in chunks of 500 rows for stability
            for i in range(0, len(update_data), 500):
                db.execute(stmt, update_data[i:i+500])
            db.commit()
            logger.info(f"Updated {symbol}: {len(update_data)} rows")
    except Exception as e:
        logger.error(f"Error processing {symbol}: {e}")
        db.rollback()
    finally:
        db.close()

def main():
    db = SessionLocal()
    symbols = [r[0] for r in db.query(HistoryPSX.symbol).distinct().all()]
    db.close()
    
    logger.info(f"Starting parallel backfill for {len(symbols)} symbols...")
    with ThreadPoolExecutor(max_workers=10) as executor:
        executor.map(process_symbol, symbols)
    logger.info("Backfill complete!")

if __name__ == "__main__":
    main()
