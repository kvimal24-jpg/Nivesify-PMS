import yfinance as yf
from datetime import date
from engine import db

SYMBOLS = {
    "Nifty 50": "^NSEI", "Sensex": "^BSESN", "Bank Nifty": "^NSEBANK",
    "USD/INR": "INR=X", "Crude (Brent)": "BZ=F", "Gold": "GC=F",
}
POLICY = {"Repo Rate": 6.5, "CPI Inflation": 4.9}   # edit here or wire RBI API later

def run():
    today = str(date.today()); rows = []
    for name, sym in SYMBOLS.items():
        try:
            h = yf.Ticker(sym).history(period="5d")
            if len(h) >= 2:
                last, prev = float(h["Close"].iloc[-1]), float(h["Close"].iloc[-2])
                rows.append((name, round(last, 2), round((last - prev) / prev * 100, 2), today, "yfinance"))
        except Exception as e: print("  macro", name, e)
    for name, val in POLICY.items():
        rows.append((name, val, None, today, "config"))
    c = db.conn(); c.executemany("INSERT OR REPLACE INTO macro VALUES(?,?,?,?,?)", rows); c.commit(); c.close()
    print(f"  {len(rows)} macro indicators")
    return rows
