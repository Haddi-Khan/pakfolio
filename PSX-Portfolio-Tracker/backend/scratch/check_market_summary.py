import sys
sys.path.insert(0, '.')
from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    # Test what change_pct distribution looks like
    stats = conn.execute(text("""
        SELECT 
            COUNT(*) FILTER (WHERE lp.change_pct > 0) as advances,
            COUNT(*) FILTER (WHERE lp.change_pct < 0) as declines,
            COUNT(*) FILTER (WHERE lp.change_pct = 0 OR lp.change_pct IS NULL) as unchanged,
            COUNT(*) as total
        FROM live_prices lp
        JOIN global_symbols gs ON gs.symbol = lp.symbol
        WHERE gs.asset_type = 'STOCK'
    """)).fetchone()
    print(f"With change_pct fix:")
    print(f"  advances={stats[0]}, declines={stats[1]}, unchanged={stats[2]}, total={stats[3]}")

    # Also sample some declining stocks
    rows = conn.execute(text("""
        SELECT lp.symbol, lp.change, lp.change_pct 
        FROM live_prices lp 
        JOIN global_symbols gs ON gs.symbol=lp.symbol 
        WHERE gs.asset_type='STOCK' AND lp.change_pct < 0 
        ORDER BY lp.change_pct ASC
        LIMIT 5
    """)).fetchall()
    print(f"\nTop 5 decliners: {rows}")
