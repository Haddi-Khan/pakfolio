import pandas as pd
import numpy as np
from database import SessionLocal
from models import HistoryPSX
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1  + rs))

def backfill_all():
    db = SessionLocal()
    try:
        # Get unique symbols that need backfill
        symbols = [r[0] for r in db.execute(text("SELECT DISTINCT symbol FROM history_psx")).fetchall()]
        logger.info(f"Starting backfill for {len(symbols)} symbols...")

        for sym in symbols:
            # Fetch all history for this symbol
            query = db.query(HistoryPSX).filter(HistoryPSX.symbol == sym).order_by(HistoryPSX.date.asc())
            df = pd.read_sql(query.statement, db.bind)
            
            if len(df) < 20:
                continue

            # Calculate indicators
            df['sma_20'] = df['close'].rolling(window=20).mean()
            df['sma_50'] = df['close'].rolling(window=50).mean()
            df['sma_200'] = df['close'].rolling(window=200).mean()
            df['std_20'] = df['close'].rolling(window=20).std()
            df['bbu_20_2_0'] = df['sma_20'] + (df['std_20'] * 2)
            df['bbl_20_2_0'] = df['sma_20'] - (df['std_20'] * 2)
            df['rsi_14'] = calculate_rsi(df['close'], 14)

            # Prepare batch update
            # We only update rows that changed (to save time)
            update_data = []
            for _, row in df.iterrows():
                if pd.isna(row['sma_20']): continue
                
                update_data.append({
                    'id': int(row['id']),
                    'sma_20': float(row['sma_20']) if not pd.isna(row['sma_20']) else None,
                    'sma_50': float(row['sma_50']) if not pd.isna(row['sma_50']) else None,
                    'sma_200': float(row['sma_200']) if not pd.isna(row['sma_200']) else None,
                    'std_20': float(row['std_20']) if not pd.isna(row['std_20']) else None,
                    'bbu_20_2_0': float(row['bbu_20_2_0']) if not pd.isna(row['bbu_20_2_0']) else None,
                    'bbl_20_2_0': float(row['bbl_20_2_0']) if not pd.isna(row['bbl_20_2_0']) else None,
                    'rsi_14': float(row['rsi_14']) if not pd.isna(row['rsi_14']) else None
                })

            if update_data:
                # Use bulk update
                stmt = text("""
                    UPDATE history_psx SET
                        sma_20 = :sma_20,
                        sma_50 = :sma_50,
                        sma_200 = :sma_200,
                        std_20 = :std_20,
                        bbu_20_2_0 = :bbu_20_2_0,
                        bbl_20_2_0 = :bbl_20_2_0,
                        rsi_14 = :rsi_14
                    WHERE id = :id
                """)
                db.execute(stmt, update_data)
                db.commit()
                logger.info(f"Updated {sym} ({len(update_data)} rows)")

    except Exception as e:
        logger.error(f"Backfill failed: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    backfill_all()
