import os
import sys
from datetime import date, timedelta

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))

import portfolio as pf

def test_cash_only_chart():
    print("Testing portfolio chart with only cash transactions...")
    
    # Mock data
    trades = []
    historical = {} # No stocks
    
    today = date.today()
    yesterday = today - timedelta(days=1)
    
    cash_timeline = [
        {"date": yesterday.isoformat(), "running_cash": 10000.0},
        {"date": today.isoformat(), "running_cash": 15000.0}
    ]
    
    chart = pf.build_portfolio_chart(trades, historical, cash_timeline)
    
    if not chart:
        print("FAILURE: Chart is empty")
        return

    print(f"Chart generated with {len(chart)} points.")
    for point in chart:
        print(f"  {point['date']}: {point['value']}")
        
    last_value = chart[-1]["value"]
    if last_value == 15000.0:
        print("SUCCESS: Last chart value matches running cash.")
    else:
        print(f"FAILURE: Expected 15000.0, got {last_value}")

if __name__ == "__main__":
    test_cash_only_chart()
