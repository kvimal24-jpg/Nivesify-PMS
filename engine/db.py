import sqlite3, os
from engine import config

DB = os.path.join(config.CACHE, "pms.sqlite")

def conn():
    os.makedirs(config.CACHE, exist_ok=True)
    c = sqlite3.connect(DB); c.row_factory = sqlite3.Row; return c

def tofloat(v):
    try:
        if v is None: return None
        if isinstance(v, (int, float)): return float(v)
        s = str(v).replace(",", "").replace("%", "").strip()
        if s in ("", "-", "—", "N/A", "NA"): return None
        return float(s)
    except: return None

def init():
    c = conn()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS companies(code TEXT PRIMARY KEY, name TEXT, sector TEXT, industry TEXT, nse TEXT);
    CREATE TABLE IF NOT EXISTS raw(code TEXT PRIMARY KEY, blob TEXT);
    CREATE TABLE IF NOT EXISTS metrics(code TEXT, section TEXT, metric TEXT, period TEXT, value REAL,
        PRIMARY KEY(code,section,metric,period));
    CREATE TABLE IF NOT EXISTS prices(nse TEXT PRIMARY KEY, price REAL, prev REAL, chg REAL, asof TEXT);
    CREATE TABLE IF NOT EXISTS scores(code TEXT, sector TEXT, score REAL, PRIMARY KEY(code,sector));
    CREATE TABLE IF NOT EXISTS sector_text(sector TEXT PRIMARY KEY, meta TEXT);
    CREATE TABLE IF NOT EXISTS macro(indicator TEXT PRIMARY KEY, value REAL, change_pct REAL, asof TEXT, source TEXT);
    """)
    c.commit(); c.close()

def reset():
    c = conn()
    for t in ["companies","raw","metrics","prices","scores","sector_text","macro"]:
        c.execute(f"DELETE FROM {t}")
    c.commit(); c.close()
