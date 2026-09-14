import os, sqlite3
from engine import config

DB = os.path.join(config.CACHE, "pms.sqlite")

def tofloat(v):
    try:
        if v is None: return None
        if isinstance(v, (int, float)): return float(v)
        s = str(v).replace(",", "").replace("%", "").strip()
        if s in ("", "-", "—"): return None
        return float(s)
    except Exception:
        return None

def conn():
    os.makedirs(config.CACHE, exist_ok=True)
    c = sqlite3.connect(DB); c.row_factory = sqlite3.Row
    return c

def init():
    c = conn()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS companies(code TEXT PRIMARY KEY, name TEXT, sector TEXT, industry TEXT, nse TEXT);
    CREATE TABLE IF NOT EXISTS raw(code TEXT PRIMARY KEY, blob TEXT);
    CREATE TABLE IF NOT EXISTS metrics(code TEXT, section TEXT, metric TEXT, period TEXT, value REAL,
        PRIMARY KEY(code,section,metric,period));
    CREATE TABLE IF NOT EXISTS pros_cons(code TEXT, kind TEXT, text TEXT);
    CREATE TABLE IF NOT EXISTS prices(nse TEXT PRIMARY KEY, price REAL, prev REAL, chg REAL, asof TEXT);
    CREATE TABLE IF NOT EXISTS scores(code TEXT PRIMARY KEY, sector TEXT, score REAL);
    CREATE TABLE IF NOT EXISTS sector_stats(sector TEXT, metric TEXT, value REAL, PRIMARY KEY(sector,metric));
    CREATE TABLE IF NOT EXISTS sector_text(sector TEXT PRIMARY KEY, meta TEXT);
    CREATE TABLE IF NOT EXISTS macro(indicator TEXT PRIMARY KEY, value REAL, change_pct REAL, asof TEXT, source TEXT);
    CREATE TABLE IF NOT EXISTS transactions(portfolio TEXT, date TEXT, code TEXT, type TEXT, qty REAL, price REAL);
    CREATE TABLE IF NOT EXISTS playbooks(sector TEXT PRIMARY KEY, name TEXT, json TEXT);
    CREATE INDEX IF NOT EXISTS idx_metrics ON metrics(section,metric,period);
    """)
    c.commit(); c.close()

def reset():
    c = conn()
    for t in ["companies","raw","metrics","pros_cons","prices","scores","sector_stats","sector_text","macro","transactions"]:
        c.execute(f"DELETE FROM {t}")
    c.commit(); c.close()

def load_latest_metrics(codes):
    if not codes: return {}
    c = conn()
    q = ",".join("?" * len(codes))
    out = {}
    for r in c.execute(f"SELECT code,section,metric,value FROM metrics WHERE period='latest' AND code IN ({q})", codes):
        out.setdefault(r["code"], {})[(r["section"], r["metric"])] = r["value"]
    c.close()
    return out
