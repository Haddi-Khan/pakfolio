import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

# Test direct connection (5432)
DIRECT_URL = "postgresql://postgres.qppdpbmhjzlrbncurckw:z4v6V_pN!tLDz8A@db.qppdpbmhjzlrbncurckw.supabase.co:5432/postgres?sslmode=require"

print("Testing direct connection (5432)...")
try:
    engine = create_engine(DIRECT_URL)
    with engine.connect() as conn:
        print("Success: ", conn.execute(text("SELECT 1")).scalar())
except Exception as e:
    print("Direct failed: ", e)

# Test pooler connection (6543)
POOLER_URL = os.getenv("DATABASE_URL")
print("\nTesting pooler connection (6543)...")
try:
    engine = create_engine(POOLER_URL)
    with engine.connect() as conn:
        print("Success: ", conn.execute(text("SELECT 1")).scalar())
except Exception as e:
    print("Pooler failed: ", e)
