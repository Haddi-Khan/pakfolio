
import os
import time
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///./psx_portfolio.db"

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Using NullPool and disabling prepared statements for the migration script too
engine = create_engine(
    DATABASE_URL, 
    poolclass=NullPool,
    connect_args={"prepare_threshold": None, "connect_timeout": 60}
)

def batch_update_table(table_name, column_name):
    print(f"Batch updating {table_name}.{column_name} to uppercase...")
    
    # We'll use a simpler approach: update by ID or just in small sets if possible.
    # But since we just want to fix the case, we can use a LIMIT if supported, 
    # or just keep trying until zero rows are left to update.
    
    query = f"""
    UPDATE {table_name} 
    SET {column_name} = UPPER({column_name}::text)::assettype
    WHERE {column_name}::text != UPPER({column_name}::text)
    AND ctid IN (
        SELECT ctid FROM {table_name} 
        WHERE {column_name}::text != UPPER({column_name}::text)
        LIMIT 5000
    )
    """
    
    total_updated = 0
    while True:
        try:
            with engine.connect() as conn:
                result = conn.execute(text(query))
                rows = result.rowcount
                conn.commit()
                
                if rows == 0:
                    print(f"Finished updating {table_name}.")
                    break
                
                total_updated += rows
                print(f"Updated {rows} rows (Total: {total_updated})...")
                time.sleep(0.5) # Small sleep to let DB breathe
        except Exception as e:
            print(f"Error during batch update: {e}")
            time.sleep(5) # Wait longer on error

if __name__ == "__main__":
    batch_update_table("trades", "asset_type")
    batch_update_table("historical_prices", "asset_type")
