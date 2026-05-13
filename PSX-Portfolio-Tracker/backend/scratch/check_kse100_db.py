import sys
sys.path.insert(0, '.')
from database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    rows = db.execute(text(
        "SELECT date, close, sma_20, sma_50, sma_200, bbu_20_2_0, bbl_20_2_0, rsi_14 "
        "FROM history_psx WHERE symbol='KSE100' ORDER BY date DESC LIMIT 10"
    )).fetchall()
    for r in rows:
        print(r)
finally:
    db.close()
