
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

def fix_pg_enum():
    with engine.connect() as conn:
        # 1. Add 'INDEX' to the enum labels
        print("Adding 'INDEX' to assettype enum...")
        try:
            # ALTER TYPE ... ADD VALUE cannot be run in a transaction in many PG environments
            # We use isolation_level='AUTOCOMMIT' for this
            with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as autocommit_conn:
                autocommit_conn.execute(text("ALTER TYPE assettype ADD VALUE 'INDEX'"))
            print("Successfully added 'INDEX' to enum.")
        except Exception as e:
            if "already exists" in str(e).lower():
                print("'INDEX' already exists in enum labels.")
            else:
                print(f"Error adding 'INDEX' to enum: {e}")

        # 2. Update data
        tables = ["trades", "historical_prices", "global_symbols"]
        for table in tables:
            print(f"Updating table: {table}")
            try:
                # Update 'index' to 'INDEX'
                # We use ::text cast to be safe and avoid enum mismatch during comparison if needed
                result = conn.execute(text(f"UPDATE {table} SET asset_type = 'INDEX' WHERE asset_type::text = 'index'"))
                # Also handle other lowercase if they exist (though not seen in labels)
                conn.execute(text(f"UPDATE {table} SET asset_type = 'STOCK' WHERE asset_type::text = 'stock'"))
                conn.execute(text(f"UPDATE {table} SET asset_type = 'MUTUAL_FUND' WHERE asset_type::text = 'mutual_fund'"))
                conn.execute(text(f"UPDATE {table} SET asset_type = 'ETF' WHERE asset_type::text = 'etf'"))
                conn.commit()
                print(f"Successfully updated {table}")
            except Exception as e:
                print(f"Error updating {table}: {e}")

if __name__ == "__main__":
    fix_pg_enum()
