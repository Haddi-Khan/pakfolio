
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

with engine.connect() as conn:
    result = conn.execute(text("SELECT DISTINCT asset_type FROM global_symbols"))
    print("Unique asset_type values in global_symbols:")
    for row in result:
        print(f"'{row[0]}'")

    result = conn.execute(text("SELECT DISTINCT asset_type FROM trades"))
    print("\nUnique asset_type values in trades:")
    for row in result:
        print(f"'{row[0]}'")
