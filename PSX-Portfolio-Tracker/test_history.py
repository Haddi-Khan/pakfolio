import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
from data_providers.sarmaaya_provider import SarmaayaProvider
from datetime import datetime, timedelta

p = SarmaayaProvider()
end = datetime.now()
start = end - timedelta(days=3650) # exactly 10 years

for sym in ["AVN", "UFSF"]:
    hist = p.get_historical(sym, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
    print(f"{sym} 10-year history points: {len(hist)}")
    if hist:
        print(f"  Earliest date: {hist[0].date}")
        print(f"  Latest date: {hist[-1].date}")
