import os
import sys

# Add backend to path so we can import models and database
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))

from sqlalchemy import text
from database import SessionLocal, engine

def fix_sequences():
    print("Fixing database sequences...")
    db = SessionLocal()
    try:
        # Get all tables that might have sequences
        # In PostgreSQL, we can use a query to finding sequences or just target the ones we know
        tables = ["users", "portfolios", "trades", "cash_transactions", "historical_prices", "password_reset_tokens"]
        
        for table in tables:
            try:
                # Find the max ID
                result = db.execute(text(f"SELECT MAX(id) FROM {table}")).fetchone()
                max_id = result[0] if result and result[0] is not None else 0
                
                # Reset sequence. Default naming in SQLAlchemy/Postgres is table_id_seq
                seq_name = f"{table}_id_seq"
                db.execute(text(f"SELECT setval('{seq_name}', {max_id + 1}, false)"))
                print(f"  - Reset {seq_name} to {max_id + 1}")
            except Exception as e:
                print(f"  - Could not reset sequence for {table}: {e}")
        
        db.commit()
        print("Done!")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    fix_sequences()
