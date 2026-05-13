
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from models import GlobalSymbol, AssetType

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///./psx_portfolio.db"

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)

def test_query():
    with Session(engine) as session:
        try:
            print("Querying GlobalSymbol...")
            results = session.query(GlobalSymbol).limit(10).all()
            for r in results:
                print(f"Symbol: {r.symbol}, AssetType: {r.asset_type}")
            print("Success!")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    test_query()
