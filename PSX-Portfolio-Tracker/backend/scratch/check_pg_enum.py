
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

def check_pg_enum():
    with engine.connect() as conn:
        try:
            result = conn.execute(text("SELECT enumlabel FROM pg_enum WHERE enumtypid = 'assettype'::regtype"))
            print("PostgreSQL Enum 'assettype' labels:")
            for row in result:
                print(f"'{row[0]}'")
        except Exception as e:
            print(f"Error checking PG enum (maybe not Postgres or type doesn't exist): {e}")

if __name__ == "__main__":
    check_pg_enum()
