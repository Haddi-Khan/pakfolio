
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

def update_asset_types():
    tables = ["trades", "historical_prices", "global_symbols"]
    with engine.connect() as conn:
        for table in tables:
            print(f"Updating table: {table}")
            try:
                # Update to uppercase
                result = conn.execute(text(f"UPDATE {table} SET asset_type = UPPER(asset_type)"))
                conn.commit()
                print(f"Successfully updated {table}")
            except Exception as e:
                print(f"Error updating {table}: {e}")

if __name__ == "__main__":
    update_asset_types()
