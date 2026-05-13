import os
import sys
from sqlalchemy import text

# Setup path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from database import SessionLocal

def migrate():
    print("Starting migration...")
    db = SessionLocal()
    try:
        # PostgreSQL syntax for altering column type
        commands = [
            "ALTER TABLE trades ALTER COLUMN symbol TYPE VARCHAR(100);",
            "ALTER TABLE historical_prices ALTER COLUMN symbol TYPE VARCHAR(100);",
            "ALTER TABLE live_prices ALTER COLUMN symbol TYPE VARCHAR(100);",
            "ALTER TABLE history_psx ADD COLUMN IF NOT EXISTS sma_50 NUMERIC(16, 4);",
            "ALTER TABLE history_psx ADD COLUMN IF NOT EXISTS sma_200 NUMERIC(16, 4);",
            "ALTER TABLE history_psx ADD COLUMN IF NOT EXISTS sma_20 NUMERIC(16, 4);",
            "ALTER TABLE history_psx ADD COLUMN IF NOT EXISTS std_20 NUMERIC(16, 4);",
            "ALTER TABLE history_psx ADD COLUMN IF NOT EXISTS bbl_20_2_0 NUMERIC(16, 4);",
            "ALTER TABLE history_psx ADD COLUMN IF NOT EXISTS bbu_20_2_0 NUMERIC(16, 4);",
            "ALTER TABLE history_psx ADD COLUMN IF NOT EXISTS rsi_14 NUMERIC(16, 4);",
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_history_psx_symbol_date ON history_psx (symbol, date);"
        ]
        
        for cmd in commands:
            print(f"Executing: {cmd}")
            db.execute(text(cmd))
        
        db.commit()
        print("Migration successful!")
    except Exception as e:
        db.rollback()
        print(f"Migration failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    migrate()
