import httpx
import json

BASE = "https://dps.psx.com.pk"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; PSXTracker/1.0)",
    "Accept": "application/json, text/html",
}

def check_quotes():
    with httpx.Client(headers=HEADERS, timeout=10) as client:
        resp = client.get(f"{BASE}/quotes")
        data = resp.json()
        print(f"Total items: {len(data)}")
        
        # Look for KSE100
        kse100 = [item for item in data if (item.get("symbol") or "").upper() == "KSE100"]
        if kse100:
            print("KSE100 found in quotes:")
            print(json.dumps(kse100[0], indent=2))
        else:
            print("KSE100 NOT found in quotes.")
            # Check for any index
            indices = [item for item in data if item.get("asset_type") == "INDEX"]
            print(f"Total indices found: {len(indices)}")
            if indices:
                print(f"Sample index symbols: {[i.get('symbol') for i in indices[:5]]}")

if __name__ == "__main__":
    check_quotes()
