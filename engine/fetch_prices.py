import os, json, yfinance as yf
import pandas as pd
import time
import random
from datetime import date
from engine import config, db

def run():
    cp = os.path.join(config.CACHE, "prices.json")
    if os.path.exists(cp):
        cached = json.load(open(cp))
        if cached.get("date") == str(date.today()) and len(cached.get("prices", {})) > 0:
            print(f"  Using cached prices ({len(cached['prices'])} tickers)")
            _store(cached["prices"]); return cached["prices"]
    
    c = db.conn()
    raw_codes = [r["nse"] for r in c.execute("SELECT DISTINCT nse FROM companies") if r["nse"]]
    c.close()
    
    codes = [c for c in raw_codes if c and "&" not in str(c) and "#" not in str(c)]
    print(f"  {len(codes)} tickers to fetch")
    
    prices = {}
    for i, code in enumerate(codes):
        try:
            if i > 0 and i % 20 == 0: time.sleep(random.uniform(2.0, 4.0))
            ticker = yf.Ticker(f"{code}.NS")
            hist = ticker.history(period="5d")
            
            if len(hist) >= 2:
                last = hist['Close'].iloc[-1]
                prev = hist['Close'].iloc[-2]
                # STRICT CHECK: Ignore pandas/numpy NaN and zero division
                if pd.isna(last) or pd.isna(prev) or prev == 0:
                    continue
                    
                last = float(last)
                prev = float(prev)
                prices[code] = {
                    "price": round(last, 2),
                    "prev": round(prev, 2),
                    "chg": round((last - prev) / prev * 100, 2)
                }
            if (i + 1) % 100 == 0: print(f"    Progress: {i+1}/{len(codes)}")
        except Exception:
            pass
    
    print(f"  Success: {len(prices)} tickers")
    json.dump({"date": str(date.today()), "prices": prices}, open(cp, "w"))
    _store(prices)
    return prices

def _store(prices):
    c = db.conn()
    c.executemany("INSERT OR REPLACE INTO prices VALUES(?,?,?,?,?)",
                  [(k, v["price"], v["prev"], v["chg"], str(date.today())) for k, v in prices.items()])
    c.commit(); c.close()
