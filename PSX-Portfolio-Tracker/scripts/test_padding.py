import os
import sys
from datetime import date

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))

import portfolio as pf

def test_single_point_padding():
    print("Testing portfolio chart padding for a single data point...")
    
    # Mock data with only ONE point
    trades = []
    historical = {}
    today = date.today().isoformat()
    cash_timeline = [{"date": today, "running_cash": 50000.0}]
    
    chart = pf.build_portfolio_chart(trades, historical, cash_timeline)
    
    print(f"Chart generated with {len(chart)} points.")
    for point in chart:
        print(f"  {point['date']}: {point['value']}")
        
    if len(chart) == 2:
        print("SUCCESS: Single point was correctly padded to 2 points.")
    else:
        print(f"FAILURE: Expected 2 points, got {len(chart)}")

if __name__ == "__main__":
    test_single_point_padding()
