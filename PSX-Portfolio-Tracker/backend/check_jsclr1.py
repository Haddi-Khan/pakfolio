import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
url = os.getenv("DATABASE_URL")
if not url:
    print("No DATABASE_URL found")
else:
    # SQLAlchemy 2.0 requires postgresql:// instead of postgres://
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    
    is_pooler = ":6543" in url
    if "sslmode" not in url:
        sep = "&" if "?" in url else "?"
        url += f"{sep}sslmode=require"

    connect_args = {
        "connect_timeout": 30,
        "gssencmode": "disable",
        "keepalives": 1,
        "keepalives_idle": 30,
        "keepalives_interval": 10,
        "keepalives_count": 5
    }

    from sqlalchemy.pool import NullPool
    try:
        engine = create_engine(url, connect_args=connect_args, poolclass=NullPool)
        with engine.connect() as conn:
            # Check HistoryPSX count
            count_res = conn.execute(text("SELECT count(*) FROM history_psx WHERE symbol = 'JSCLR1'"))
            print(f"Total rows for JSCLR1: {count_res.scalar()}")

            print("\n--- Latest 5 from HistoryPSX for JSCLR1 ---")
            res = conn.execute(text("SELECT * FROM history_psx WHERE symbol = 'JSCLR1' ORDER BY date DESC LIMIT 5"))
            rows = res.fetchall()
            for r in rows:
                print(r)
            
            # Check LivePrice
            print("\n--- LivePrice for JSCLR1 ---")
            res = conn.execute(text("SELECT * FROM live_prices WHERE symbol = 'JSCLR1'"))
            row = res.fetchone()
            print(row)
            
    except Exception as e:
        print(f"Error: {e}")
