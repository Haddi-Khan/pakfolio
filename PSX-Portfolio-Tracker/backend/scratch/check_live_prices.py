import sys
sys.path.insert(0, '.')
from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    stats = conn.execute(text("""
        SELECT 
            COUNT(*) FILTER (WHERE lp.change > 0) as advances,
            COUNT(*) FILTER (WHERE lp.change < 0) as declines,
            COUNT(*) FILTER (WHERE lp.change = 0 OR lp.change IS NULL) as unchanged,
            COUNT(*) FILTER (WHERE lp.change_pct IS NULL) as no_pct,
            COUNT(*) as total
        FROM live_prices lp
        JOIN global_symbols gs ON gs.symbol = lp.symbol
        WHERE gs.asset_type = 'STOCK'
    """)).fetchone()
    print(f"advances={stats[0]}, declines={stats[1]}, unchanged={stats[2]}, no_pct={stats[3]}, total={stats[4]}")
    
    # Sample some declining stocks
    rows = conn.execute(text(
        "SELECT lp.symbol, lp.change, lp.change_pct FROM live_prices lp JOIN global_symbols gs ON gs.symbol=lp.symbol WHERE gs.asset_type='STOCK' AND lp.change < 0 LIMIT 5"
    )).fetchall()
    print("declining samples:", rows)
    
    # Sample some with no change_pct
    rows2 = conn.execute(text(
        "SELECT lp.symbol, lp.change, lp.change_pct FROM live_prices lp JOIN global_symbols gs ON gs.symbol=lp.symbol WHERE gs.asset_type='STOCK' AND lp.change_pct IS NULL LIMIT 5"
    )).fetchall()
    print("no change_pct samples:", rows2)
    
    # Sample a few stocks with change=0
    rows3 = conn.execute(text(
        "SELECT lp.symbol, lp.price, lp.change, lp.change_pct, lp.prev_close FROM live_prices lp JOIN global_symbols gs ON gs.symbol=lp.symbol WHERE gs.asset_type='STOCK' AND lp.change = 0 LIMIT 5"
    )).fetchall()
    print("change=0 samples:", rows3)
