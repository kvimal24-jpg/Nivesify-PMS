import os, json, yfinance as yf
import time
import random
from datetime import date
from engine import config, db

def run():
    cp = os.path.join(config.CACHE, "prices.json")
    
    # Check cache - but verify it has data
    if os.path.exists(cp):
        cached = json.load(open(cp))
        if cached.get("date") == str(date.today()) and len(cached.get("prices", {})) > 0:
            print(f"  Using cached prices ({len(cached['prices'])} tickers)")
            _store(cached["prices"])
            return cached["prices"]
        else:
            print(f"  Cache empty or stale, refetching...")
    
    c = db.conn()
    raw_codes = [r["nse"] for r in c.execute("SELECT DISTINCT nse FROM companies") if r["nse"]]
    c.close()
    
    # Filter and clean codes
    codes = []
    for code in raw_codes:
        if code and "&" not in str(code) and "#" not in str(code) and len(str(code)) > 2:
            codes.append(str(code).strip())
    
    print(f"  {len(codes)} valid tickers to fetch")
    
    if len(codes) == 0:
        print("  ERROR: No valid tickers found!")
        return {}
    
    prices = {}
    failed = []
    rate_limit_count = 0
    
    # Test with first 5 tickers to verify it works
    print("  Testing with first 5 tickers...")
    for code in codes[:5]:
        try:
            ticker = yf.Ticker(f"{code}.NS")
            hist = ticker.history(period="5d")
            if len(hist) >= 2:
                last = float(hist['Close'].iloc[-1])
                prev = float(hist['Close'].iloc[-2])
                prices[code] = {
                    "price": round(last, 2),
                    "prev": round(prev, 2),
                    "chg": round((last - prev) / prev * 100, 2)
                }
                print(f"    ✓ {code}: ₹{prices[code]['price']}")
            time.sleep(1)
        except Exception as e:
            print(f"    ✗ {code}: {type(e).__name__}")
            failed.append(code)
    
    if len(prices) == 0:
        print("  ERROR: Test fetch failed! Check network/yfinance.")
        return {}
    
    print(f"  Test successful! Fetching remaining {len(codes)-5} tickers...")
    
    # Fetch remaining tickers
    for i, code in enumerate(codes[5:], start=5):
        try:
            # Rate limiting protection
            if i > 0 and i % 20 == 0:
                time.sleep(random.uniform(3.0, 6.0))
            
            ticker = yf.Ticker(f"{code}.NS")
            hist = ticker.history(period="5d")
            
            if len(hist) >= 2:
                last = float(hist['Close'].iloc[-1])
                prev = float(hist['Close'].iloc[-2])
                prices[code] = {
                    "price": round(last, 2),
                    "prev": round(prev, 2),
                    "chg": round((last - prev) / prev * 100, 2)
                }
                
            if (i + 1) % 100 == 0:
                print(f"    Progress: {i+1}/{len(codes)} ({len(prices)} successful)")
                
        except Exception as e:
            error_msg = str(e)
            if "Rate" in error_msg or "Too Many" in error_msg or "429" in error_msg:
                rate_limit_count += 1
                if rate_limit_count <= 3:  # Only wait first 3 times
                    print(f"  Rate limited at {i}, waiting 90 seconds...")
                    time.sleep(90)
                    rate_limit_count = 0
            failed.append(code)
    
    print(f"\n  RESULTS:")
    print(f"    Successful: {len(prices)} tickers")
    print(f"    Failed: {len(failed)} tickers")
    if len(failed) > 0 and len(failed) <= 20:
        print(f"    Failed codes: {failed[:20]}")
    
    # Save cache
    json.dump({"date": str(date.today()), "prices": prices}, open(cp, "w"))
    _store(prices)
    return prices

def _store(prices):
    c = db.conn()
    c.executemany("INSERT OR REPLACE INTO prices VALUES(?,?,?,?,?)",
                  [(k, v["price"], v["prev"], v["chg"], str(date.today())) for k, v in prices.items()])
    c.commit()
    c.close()
    print(f"  Stored {len(prices)} prices in database")
