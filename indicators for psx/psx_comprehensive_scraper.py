import pandas as pd
import requests
import yfinance as yf
from bs4 import BeautifulSoup
import time
import random
import os
import json
import logging
import contextlib

# Suppress yfinance warnings
logging.getLogger("yfinance").setLevel(logging.CRITICAL)


class FreeProxyManager:
    """Manages free proxies scraped from the web to prevent IP blocking."""

    def __init__(self):
        self.proxies = []
        self.update_proxies()

    def update_proxies(self):
        print("Updating proxy list...")
        try:
            res = requests.get("https://free-proxy-list.net/", timeout=10)
            soup = BeautifulSoup(res.text, "html.parser")
            table = soup.find("table")
            proxies = []
            if table and table.tbody:
                for row in table.tbody.find_all("tr")[
                    :50
                ]:  # Get top 50 proxies
                    cols = row.find_all("td")
                    if len(cols) >= 2:
                        ip = cols[0].text.strip()
                        port = cols[1].text.strip()
                        proxies.append(f"http://{ip}:{port}")
            self.proxies = proxies
            print(f"Found {len(self.proxies)} proxies.")
        except Exception as e:
            print(f"Failed to fetch proxies: {e}")

    def get_proxy(self):
        if not self.proxies:
            return None
        proxy = random.choice(self.proxies)
        return {"http": proxy, "https": proxy}


class PSXScraper:
    def __init__(self, use_proxies=True):
        self.use_proxies = use_proxies
        self.proxy_manager = FreeProxyManager() if use_proxies else None
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36"
                )
            }
        )
        self.base_url = "https://dps.psx.com.pk"

    def _get(self, url, **kwargs):
        for attempt in range(3):
            if (
                self.use_proxies
                and self.proxy_manager
                and self.proxy_manager.proxies
            ):
                proxy = self.proxy_manager.get_proxy()
                kwargs["proxies"] = proxy
                try:
                    res = self.session.get(url, timeout=5, **kwargs)
                    return res
                except Exception:
                    if proxy:
                        proxy_url = proxy.get("http")
                        if proxy_url in self.proxy_manager.proxies:
                            self.proxy_manager.proxies.remove(proxy_url)
            
            try:
                # Direct fallback
                return self.session.get(url, timeout=10)
            except Exception:
                time.sleep(1)  # wait before retry
        return None

    def get_all_symbols(self):
        """Fetches all registered companies on PSX."""
        print("Fetching all PSX symbols...")
        res = self._get(f"{self.base_url}/symbols")
        if res and res.status_code == 200:
            try:
                # Exclude bonds/debt instruments
                symbols = [
                    x["symbol"] for x in res.json() 
                    if x.get("symbol") and not x.get("isDebt", False)
                ]
                print(f"Found {len(symbols)} equity symbols (excluding bonds).")
                return symbols
            except Exception:
                pass
        print("Failed to fetch symbols. Please check your connection.")
        return []

    def get_historical_ohlcv(self, symbol):
        """Fetches max historical OHLCV data by comparing PSX DPS and Yahoo Finance."""
        # 1. Fetch from Yahoo Finance (often has data back to 2008)
        df_yf = self._get_history_from_yahoo(symbol)
        
        # 2. Fetch from PSX DPS
        df_psx = pd.DataFrame()
        url = f"{self.base_url}/historical"
        kwargs = {"data": {"symbol": symbol}}

        if self.use_proxies and self.proxy_manager and self.proxy_manager.proxies:
            kwargs["proxies"] = self.proxy_manager.get_proxy()

        try:
            res = self.session.post(url, timeout=10, **kwargs)
        except Exception:
            try:
                kwargs.pop("proxies", None)
                res = self.session.post(url, timeout=10, **kwargs)
            except Exception:
                res = None

        if res and res.status_code == 200:
            try:
                soup = BeautifulSoup(res.text, "html.parser")
                rows = soup.find_all("tr")
                parsed_data = []
                for row in rows:
                    cols = row.find_all("td")
                    if len(cols) >= 6:
                        parsed_data.append(
                            {
                                "Date": cols[0].text.strip(),
                                "Open": cols[1].text.strip().replace(",", ""),
                                "High": cols[2].text.strip().replace(",", ""),
                                "Low": cols[3].text.strip().replace(",", ""),
                                "Close": cols[4].text.strip().replace(",", ""),
                                "Volume": cols[5].text.strip().replace(",", ""),
                            }
                        )
                if parsed_data:
                    df_psx = pd.DataFrame(parsed_data)
                    df_psx["Date"] = pd.to_datetime(df_psx["Date"], errors="coerce")
                    df_psx = df_psx.dropna(subset=["Date"]).set_index("Date").sort_index()
                    for col in ["Open", "High", "Low", "Close", "Volume"]:
                        df_psx[col] = pd.to_numeric(df_psx[col], errors="coerce")
            except Exception as e:
                print(f"Error parsing history from DPS for {symbol}: {e}")
                
        # Compare sources and pick the one with the longest history
        if not df_yf.empty and len(df_yf) >= len(df_psx):
            df = df_yf
        elif not df_psx.empty:
            df = df_psx
        else:
            return pd.DataFrame()
            
        df = self._calculate_technical_indicators(df)
        return df

    def _get_history_from_yahoo(self, symbol):
        """Fallback method to fetch historical data from Yahoo Finance."""
        try:
            with open(os.devnull, "w") as devnull:
                with contextlib.redirect_stdout(devnull), contextlib.redirect_stderr(devnull):
                    tkr = yf.Ticker(f"{symbol}.KA")
                    df = tkr.history(period="max")
            
            if df.empty:
                return pd.DataFrame()
                
            df = df.reset_index()
            # Keep only standard columns
            cols_to_keep = ["Date", "Open", "High", "Low", "Close", "Volume"]
            df = df[[c for c in cols_to_keep if c in df.columns]]
            
            # Remove fake "filler" days with 0 volume (where prices are just duplicated)
            df = df[df["Volume"] > 0]
            
            df["Date"] = pd.to_datetime(df["Date"], utc=True).dt.tz_localize(None)
            df = df.set_index("Date").sort_index()
            return df
        except Exception:
            return pd.DataFrame()

    def _calculate_technical_indicators(self, df):
        """Calculates RSI, MA, and Bollinger Bands manually using pandas."""
        if df.empty or len(df) < 20:
            return df
        try:
            for col in ["Open", "High", "Low", "Close", "Volume"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")

            # SMA 50 and 200
            df["SMA_50"] = df["Close"].rolling(window=50).mean()
            df["SMA_200"] = df["Close"].rolling(window=200).mean()

            # Bollinger Bands (20, 2)
            df["SMA_20"] = df["Close"].rolling(window=20).mean()
            df["STD_20"] = df["Close"].rolling(window=20).std()
            df["BBL_20_2.0"] = df["SMA_20"] - (df["STD_20"] * 2)
            df["BBU_20_2.0"] = df["SMA_20"] + (df["STD_20"] * 2)

            # RSI 14
            delta = df["Close"].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df["RSI_14"] = 100 - (100 / (1 + rs))

        except Exception as e:
            print(f"Error calculating technicals: {e}")
        return df

    def get_fundamentals(self, symbol):
        """Scrapes fundamental indicators."""
        fundamentals = {
            "Symbol": symbol,
            "EPS": None,
            "PE_Ratio": None,
            "Dividend_Yield": None,
            "ROE": None,
            "Book_Value": None,
            "Debt_to_Equity": None,
        }

        # 1. Scrape from PSX DPS
        url = f"{self.base_url}/company/{symbol}"
        res = self._get(url)
        if res and res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")

            for table in soup.find_all("table"):
                for tr in table.find_all("tr"):
                    row_text = [
                        td.text.strip() for td in tr.find_all(["th", "td"])
                    ]
                    if not row_text:
                        continue
                    title = row_text[0].lower()
                    if title == "eps" and len(row_text) > 1:
                        fundamentals["EPS"] = row_text[1]

            price_div = soup.find("div", class_="quote__close")
            if price_div and fundamentals["EPS"]:
                try:
                    price_text = (
                        price_div.text.replace("Rs.", "")
                        .replace(",", "")
                        .strip()
                    )
                    price = float(price_text)
                    eps_str = (
                        fundamentals["EPS"]
                        .replace(",", "")
                        .replace("(", "-")
                        .replace(")", "")
                    )
                    eps = float(eps_str)
                    if eps != 0:
                        fundamentals["PE_Ratio"] = round(price / eps, 2)
                except Exception:
                    pass

        # 2. Fetch from Yahoo Finance
        try:
            with open(os.devnull, "w") as devnull:
                with contextlib.redirect_stdout(
                    devnull
                ), contextlib.redirect_stderr(devnull):
                    tkr = yf.Ticker(f"{symbol}.KA")
                    info = tkr.info
            if info:
                fundamentals["Dividend_Yield"] = info.get("dividendYield")
                fundamentals["ROE"] = info.get("returnOnEquity")
                fundamentals["Book_Value"] = info.get("bookValue")
                fundamentals["Debt_to_Equity"] = info.get("debtToEquity")
                if not fundamentals["EPS"]:
                    fundamentals["EPS"] = info.get("trailingEps")
                if not fundamentals["PE_Ratio"]:
                    fundamentals["PE_Ratio"] = info.get("trailingPE")
        except Exception:
            pass

        return fundamentals


def get_macroeconomic_indicators():
    """Fetches macroeconomic context for Pakistan."""
    print("Fetching Macroeconomic Indicators...")
    macro = {}
    import re

    try:
        with open(os.devnull, "w") as devnull:
            with contextlib.redirect_stdout(
                devnull
            ), contextlib.redirect_stderr(devnull):
                pkr = yf.Ticker("PKR=X")
                hist = pkr.history(period="1d")
        if not hist.empty:
            macro["PKR_USD_Exchange_Rate"] = round(hist["Close"].iloc[-1], 2)
    except Exception:
        macro["PKR_USD_Exchange_Rate"] = None

    try:
        with open(os.devnull, "w") as devnull:
            with contextlib.redirect_stdout(
                devnull
            ), contextlib.redirect_stderr(devnull):
                kse = yf.Ticker("^KSE")
                hist = kse.history(period="1d")
        if not hist.empty:
            macro["KSE100_Close"] = round(hist["Close"].iloc[-1], 2)
    except Exception:
        macro["KSE100_Close"] = None

    # Fetch Policy Rate from State Bank of Pakistan
    macro["Policy_Rate"] = "See SBP (State Bank of Pakistan) website"
    try:
        res_sbp = requests.get(
            "https://www.sbp.org.pk/index.html",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10
        )
        if res_sbp.status_code == 200:
            match = re.search(r'policy rate.*?to\s*(\d+(?:\.\d+)?%)', res_sbp.text, re.IGNORECASE)
            if match:
                macro["Policy_Rate"] = match.group(1)
    except Exception as e:
        print(f"Error fetching SBP Policy Rate: {e}")

    # Fetch Inflation (CPI) from Trading Economics
    macro["Inflation_CPI"] = "See PBS (Pakistan Bureau of Statistics) website"
    try:
        res_cpi = requests.get(
            "https://tradingeconomics.com/pakistan/inflation-cpi",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10
        )
        if res_cpi.status_code == 200:
            soup = BeautifulSoup(res_cpi.text, "html.parser")
            trs = soup.find_all("tr")
            for tr in trs:
                tds = [td.text.strip() for td in tr.find_all("td") if td.text.strip()]
                if len(tds) >= 2 and tds[0] == "Inflation Rate YoY":
                    val = tds[1].replace("%", "").strip()
                    macro["Inflation_CPI"] = f"{val}%"
                    break
    except Exception as e:
        print(f"Error fetching Inflation CPI: {e}")

    return macro


def main():
    os.makedirs("output/historical_data", exist_ok=True)

    scraper = PSXScraper(use_proxies=True)

    macro_data = get_macroeconomic_indicators()
    with open("output/macroeconomics.json", "w") as f:
        json.dump(macro_data, f, indent=4)
    print("Macroeconomic data saved.")

    symbols = scraper.get_all_symbols()
    if not symbols:
        print("No symbols found. Exiting.")
        return

    # Provide a progress indication.
    # To test quickly, you can uncomment: symbols = symbols[:5]

    fundamentals_list = []

    print(f"Starting data extraction for {len(symbols)} companies...")
    for i, symbol in enumerate(symbols):
        print(f"[{i+1}/{len(symbols)}] Processing {symbol}...")

        df = scraper.get_historical_ohlcv(symbol)
        if not df.empty:
            csv_path = f"output/historical_data/{symbol}_history.csv"
            try:
                df.to_csv(csv_path)
            except PermissionError:
                print(f"  -> Error: Could not save '{csv_path}'. Is it open in Excel?")
            except Exception as e:
                print(f"  -> Error saving '{csv_path}': {e}")
        else:
            # Completely remove the 'Skipped' print statement to keep the console clean
            pass

        fund_data = scraper.get_fundamentals(symbol)
        fundamentals_list.append(fund_data)

        time.sleep(random.uniform(0.5, 1.5))

    if fundamentals_list:
        df_fund = pd.DataFrame(fundamentals_list)
        try:
            df_fund.to_csv("output/fundamentals.csv", index=False)
            print("Fundamentals data saved.")
        except PermissionError:
            print("Error: Could not save 'output/fundamentals.csv'. Please close the file if it's open.")
        except Exception as e:
            print(f"Error saving fundamentals: {e}")

    print("Scraping complete! All data saved in the 'output' directory.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[!] Script was manually stopped by the user (Ctrl+C).")
