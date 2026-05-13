import sys
import os
from datetime import date, timedelta

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from data_providers.composite_provider import CompositeProvider

def verify_stabilization():
    provider = CompositeProvider()
    
    print("--- 1. Verifying Mutual Fund History ---")
    mf_symbol = "ALHIIF" # Alhamra Islamic Income Fund
    today = date.today().isoformat()
    from_date = (date.today() - timedelta(days=30)).isoformat()
    
    mf_history = provider.get_historical(mf_symbol, from_date, today)
    print(f"Mutual Fund {mf_symbol} history entries: {len(mf_history)}")
    if mf_history:
        print(f"  Recent NAV: {mf_history[-1].close} on {mf_history[-1].date}")
    
    print("\n--- 2. Verifying Stock Quotes with Fallback ---")
    stock_symbols = ["AVN", "NCPL"]
    quotes = provider.get_quotes_bulk(stock_symbols)
    for sym in stock_symbols:
        q = quotes.get(sym)
        print(f"Stock {sym}: Price={q.price}, Change={q.change}, Open={q.open}")
        if q.price is None:
            print(f"  FAILED: No price for {sym}")
        else:
            print(f"  SUCCESS: Price fetched for {sym}")

if __name__ == "__main__":
    verify_stabilization()
