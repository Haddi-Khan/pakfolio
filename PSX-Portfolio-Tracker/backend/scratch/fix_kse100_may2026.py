"""
Fix KSE100 Missing Data: May 7-8, 2026
========================================
Uses the same CompositeProvider (Sarmaaya) that the scheduler uses.
Fetches a 300-day window of KSE100 data, recalculates ALL indicators
accurately using pandas rolling windows, then upserts everything into
history_psx so the graph shows complete BBU/BBL/SMA50/SMA200 lines.
"""
import sys, math
sys.path.insert(0, '.')

from datetime import date, timedelta, datetime
import pandas as pd

from database import engine
from sqlalchemy import text
from data_providers.composite_provider import CompositeProvider

TARGET_SYMBOL  = "KSE100"
TODAY          = date.today().isoformat()
LOOKBACK_DAYS  = 350   # 200+ days needed for SMA200 accuracy
IND_START      = (date.today() - timedelta(days=LOOKBACK_DAYS)).isoformat()

print("=" * 60)
print("KSE100 Gap-Fill & Indicator Fix")
print(f"Target: {TARGET_SYMBOL}")
print(f"Window: {IND_START} to {TODAY}")
print("=" * 60)

# -- 1. Fetch historical data via CompositeProvider (Sarmaaya) --
provider = CompositeProvider()
print(f"\nFetching KSE100 history from Sarmaaya...")
points = provider.get_historical(TARGET_SYMBOL, IND_START, TODAY)

if not points:
    print("Sarmaaya returned no data. Trying Yahoo Finance fallback...")
    import yfinance as yf
    from data_providers.base import OHLCVPoint
    
    # Try alternate Yahoo Finance tickers
    for yfTicker in ["^KSE100", "KSE100.KA", "KHI.KA"]:
        try:
            ticker = yf.Ticker(yfTicker)
            hist = ticker.history(start=IND_START, end=TODAY, auto_adjust=True)
            if not hist.empty:
                print(f"Yahoo Finance returned {len(hist)} rows for {yfTicker}")
                points = [
                    OHLCVPoint(
                        date=idx.strftime("%Y-%m-%d"),
                        open=float(row["Open"]) if row.get("Open") else None,
                        high=float(row["High"]) if row.get("High") else None,
                        low=float(row["Low"]) if row.get("Low") else None,
                        close=float(row["Close"]) if row.get("Close") else None,
                        volume=int(row["Volume"] or 0)
                    )
                    for idx, row in hist.iterrows()
                ]
                break
        except Exception as e:
            print(f"  {yfTicker} failed: {e}")

if not points:
    print("ERROR: Could not fetch KSE100 data from any source!")
    sys.exit(1)

print(f"Got {len(points)} data points")
print(f"  First: {points[0].date}  Last: {points[-1].date}")

# -- 2. Build DataFrame and compute ALL indicators --
df = pd.DataFrame([{
    "date":   p.date,
    "open":   p.open,
    "high":   p.high,
    "low":    p.low,
    "close":  p.close,
    "volume": p.volume or 0,
} for p in points]).sort_values("date").reset_index(drop=True)

c = df["close"]
df["sma_20"]     = c.rolling(20).mean()
df["sma_50"]     = c.rolling(50).mean()
df["sma_200"]    = c.rolling(200).mean()
std_20           = c.rolling(20).std()
df["bbu_20_2_0"] = df["sma_20"] + std_20 * 2
df["bbl_20_2_0"] = df["sma_20"] - std_20 * 2

delta = c.diff()
gain  = delta.clip(lower=0).rolling(14).mean()
loss  = (-delta.clip(upper=0)).rolling(14).mean()
df["rsi_14"] = 100 - (100 / (1 + gain / loss.replace(0, float("nan"))))

def _safe(v):
    if v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v))):
        return None
    return round(float(v), 4)

# Check May 7 and May 8 data
print("\nKey dates check:")
for check_date in ["2026-05-06", "2026-05-07", "2026-05-08"]:
    rows = df[df["date"] == check_date]
    if len(rows) > 0:
        r = rows.iloc[0]
        print(f"  {check_date}: close={_safe(r['close'])}, "
              f"sma50={_safe(r['sma_50'])}, sma200={_safe(r['sma_200'])}, "
              f"bbu={_safe(r['bbu_20_2_0'])}, bbl={_safe(r['bbl_20_2_0'])}")
    else:
        print(f"  {check_date}: NOT in fetched data (market closed on this day)")

# -- 3. Upsert all rows into history_psx --
all_rows = df.to_dict("records")
print(f"\nUpserting {len(all_rows)} rows into history_psx for {TARGET_SYMBOL}...")

CHUNK = 50
total_saved = 0

with engine.connect() as conn:
    # Show current DB state
    result = conn.execute(text(
        "SELECT date, close, sma_50, sma_200, bbu_20_2_0, bbl_20_2_0 "
        "FROM history_psx WHERE symbol='KSE100' "
        "ORDER BY date DESC LIMIT 5"
    )).fetchall()
    print("\nDB state BEFORE update (last 5 rows):")
    for row in result:
        print(f"  {row}")

    # Upsert in chunks
    for start in range(0, len(all_rows), CHUNK):
        chunk = all_rows[start:start + CHUNK]
        params = {}
        clauses = []
        for j, r in enumerate(chunk):
            params.update({
                f"s{j}":     TARGET_SYMBOL,
                f"d{j}":     r["date"],
                f"o{j}":     _safe(r["open"]),
                f"h{j}":     _safe(r["high"]),
                f"l{j}":     _safe(r["low"]),
                f"c{j}":     _safe(r["close"]),
                f"v{j}":     int(r["volume"] or 0),
                f"s20_{j}":  _safe(r["sma_20"]),
                f"s50_{j}":  _safe(r["sma_50"]),
                f"s200_{j}": _safe(r["sma_200"]),
                f"bbu_{j}":  _safe(r["bbu_20_2_0"]),
                f"bbl_{j}":  _safe(r["bbl_20_2_0"]),
                f"rsi_{j}":  _safe(r["rsi_14"]),
            })
            clauses.append(
                f"(:s{j},:d{j},:o{j},:h{j},:l{j},:c{j},:v{j},"
                f":s20_{j},:s50_{j},:s200_{j},:bbu_{j},:bbl_{j},:rsi_{j})"
            )

        conn.execute(text(f"""
            INSERT INTO history_psx
                (symbol, date, open, high, low, close, volume,
                 sma_20, sma_50, sma_200, bbu_20_2_0, bbl_20_2_0, rsi_14)
            VALUES {', '.join(clauses)}
            ON CONFLICT (symbol, date) DO UPDATE SET
                open        = EXCLUDED.open,
                high        = EXCLUDED.high,
                low         = EXCLUDED.low,
                close       = EXCLUDED.close,
                volume      = EXCLUDED.volume,
                sma_20      = EXCLUDED.sma_20,
                sma_50      = EXCLUDED.sma_50,
                sma_200     = EXCLUDED.sma_200,
                bbu_20_2_0  = EXCLUDED.bbu_20_2_0,
                bbl_20_2_0  = EXCLUDED.bbl_20_2_0,
                rsi_14      = EXCLUDED.rsi_14
        """), params)
        conn.commit()
        total_saved += len(chunk)
        print(f"  Saved {total_saved}/{len(all_rows)} rows...", flush=True)

    # -- 4. Verify DB state after update --
    result = conn.execute(text(
        "SELECT date, close, sma_50, sma_200, bbu_20_2_0, bbl_20_2_0, rsi_14 "
        "FROM history_psx WHERE symbol='KSE100' "
        "ORDER BY date DESC LIMIT 7"
    )).fetchall()
    print("\nDB state AFTER update (last 7 rows):")
    for row in result:
        print(f"  {row}")

    cnt = conn.execute(text(
        "SELECT COUNT(*) FROM history_psx WHERE symbol='KSE100'"
    )).scalar()
    print(f"\nTotal KSE100 rows in history_psx: {cnt}")

print(f"\n{'='*60}")
print(f"Done! {total_saved} rows upserted into history_psx.")
print(f"  Graph should now show data through {all_rows[-1]['date']}")
print(f"  with complete BBU, BBL, SMA50, SMA200 lines.")
print(f"\nNOTE: The backend cache has a 30-min TTL.")
print(f"To see changes immediately, restart the backend server.")
print("=" * 60)
