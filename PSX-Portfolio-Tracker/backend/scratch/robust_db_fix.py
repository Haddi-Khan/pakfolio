
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///./psx_portfolio.db"

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)

def robust_fix():
    # 1. Add 'INDEX' to Enum labels
    print("Ensuring 'INDEX' is in assettype enum...")
    try:
        with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            # Check if it exists first to avoid error
            labels = conn.execute(text("SELECT enumlabel FROM pg_enum WHERE enumtypid = 'assettype'::regtype")).scalars().all()
            if 'INDEX' not in labels:
                print("Adding 'INDEX' label...")
                conn.execute(text("ALTER TYPE assettype ADD VALUE 'INDEX'"))
                print("Added 'INDEX' label.")
            else:
                print("'INDEX' label already exists.")
    except Exception as e:
        print(f"Error handling Enum labels: {e}")

    # 2. Update data to uppercase
    tables = ["trades", "historical_prices", "global_symbols"]
    with engine.connect() as conn:
        for table in tables:
            print(f"Updating table: {table}")
            try:
                # Use a single UPDATE statement with case for efficiency
                # but need to cast to text and back
                stmt = f"""
                UPDATE {table} 
                SET asset_type = UPPER(asset_type::text)::assettype
                WHERE asset_type::text != UPPER(asset_type::text)
                """
                conn.execute(text(stmt))
                conn.commit()
                print(f"Successfully updated {table}")
            except Exception as e:
                print(f"Error updating {table}: {e}")
                conn.rollback()

if __name__ == "__main__":
    robust_fix()
