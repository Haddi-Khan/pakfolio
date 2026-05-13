"""
Fast KSE100 Indicator Backfill - Uses a single bulk UPDATE with CASE statements
Much faster than row-by-row updates.
"""
import sys, math
sys.path.insert(0, '.')

import pandas as pd
from database import engine
from sqlalchemy import text

print("=== KSE100 Fast Indicator Backfill ===")

with engine.connect() as conn:
    # 1. Load ALL KSE100 history ordered by date
    df = pd.read_sql(
        text("SELECT id, date, close FROM history_psx WHERE symbol='KSE100' ORDER BY date ASC"),
        conn
    )
    print(f"Total rows: {len(df)}")
    print(f"Date range: {df['date'].iloc[0]} to {df['date'].iloc[-1]}")

    if len(df) < 20:
        print("Not enough data!")
        sys.exit(1)

    # 2. Compute ALL indicators at once using pandas
    c = df["close"]
    df["sma_20"]     = c.rolling(20).mean()
    df["sma_50"]     = c.rolling(50).mean()
    df["sma_200"]    = c.rolling(200).mean()
    df["std_20"]     = c.rolling(20).std()
    df["bbu_20_2_0"] = df["sma_20"] + df["std_20"] * 2
    df["bbl_20_2_0"] = df["sma_20"] - df["std_20"] * 2

    delta = c.diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    df["rsi_14"] = 100 - (100 / (1 + gain / loss.replace(0, float("nan"))))

    def _safe(v):
        if v is None: return None
        try:
            f = float(v)
            return None if math.isnan(f) else round(f, 4)
        except:
            return None

    # 3. Only update rows that have valid (non-NaN) sma_20
    valid = df[df["sma_20"].notna()].copy()
    print(f"Rows with valid indicators: {len(valid)}")

    # 4. Batch update in chunks of 500 using temp table approach (fastest)
    CHUNK = 500
    total_updated = 0

    for start in range(0, len(valid), CHUNK):
        chunk = valid.iloc[start:start + CHUNK]
        
        # Build a VALUES list for a bulk update via JOIN
        value_rows = []
        params = {}
        for i, (_, row) in enumerate(chunk.iterrows()):
            params[f"id{i}"]   = int(row["id"])
            params[f"s20_{i}"] = _safe(row["sma_20"])
            params[f"s50_{i}"] = _safe(row["sma_50"])
            params[f"s200_{i}"]= _safe(row["sma_200"])
            params[f"bbu_{i}"] = _safe(row["bbu_20_2_0"])
            params[f"bbl_{i}"] = _safe(row["bbl_20_2_0"])
            params[f"rsi_{i}"] = _safe(row["rsi_14"])
            value_rows.append(
                f"(:id{i}::int, :s20_{i}::numeric, :s50_{i}::numeric, "
                f":s200_{i}::numeric, :bbu_{i}::numeric, :bbl_{i}::numeric, :rsi_{i}::numeric)"
            )

        sql = f"""
            UPDATE history_psx AS t
            SET
                sma_20     = v.sma_20,
                sma_50     = v.sma_50,
                sma_200    = v.sma_200,
                bbu_20_2_0 = v.bbu,
                bbl_20_2_0 = v.bbl,
                rsi_14     = v.rsi
            FROM (VALUES {', '.join(value_rows)})
                AS v(id, sma_20, sma_50, sma_200, bbu, bbl, rsi)
            WHERE t.id = v.id
        """
        conn.execute(text(sql), params)
        conn.commit()
        total_updated += len(chunk)
        print(f"  Updated {total_updated}/{len(valid)} rows...", flush=True)

    print(f"\nAll {total_updated} rows updated!")

    # 5. Verify the last 5 rows
    check = conn.execute(text(
        "SELECT date, close, sma_20, sma_50, sma_200, bbu_20_2_0, bbl_20_2_0, rsi_14 "
        "FROM history_psx WHERE symbol='KSE100' ORDER BY date DESC LIMIT 5"
    )).fetchall()
    print("\n=== Latest 5 rows after fix ===")
    for r in check:
        print(r)

print("\nBackfill complete!")
