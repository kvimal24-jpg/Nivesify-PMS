import os, json, requests, pandas as pd
from engine import config, db

def download():
    os.makedirs(config.CACHE, exist_ok=True)
    mp = os.path.join(config.CACHE, "master_data.json")
    if not os.path.exists(mp):
        r = requests.get(f"{config.DATA_LAKE}/master_data.json", timeout=600)
        r.raise_for_status(); open(mp, "wb").write(r.content)
    cp = os.path.join(config.CACHE, "eligible_mapped.csv")
    if not os.path.exists(cp):
        r = requests.get(f"{config.DATA_LAKE}/eligible_mapped.csv", timeout=120)
        r.raise_for_status(); open(cp, "wb").write(r.content)
    master = json.load(open(mp, encoding="utf-8"))
    mapped = pd.read_csv(cp, dtype={"BSE_Code": str})
    mapped["BSE_Code"] = mapped["BSE_Code"].astype(str).str.strip().str.zfill(6)
    return master, mapped

def normalize(master, mapped):
    c = db.conn()
    companies, metrics, raws = [], [], []
    
    for _, row in mapped.iterrows():
        code = row["BSE_Code"]; raw = master.get(code)
        if not raw: continue
        companies.append((code, row["Company_Name"], row["Sector"], row["Industry"], str(row["NSE_Code"])))
        raws.append((code, json.dumps(raw)))
        
        # STRICTLY PARSE THE DATA LAKE STRUCTURE (headers/data)
        for section in ["quarters", "profitLoss", "balanceSheet", "cashFlow", "ratios", "shareholding"]:
            body = raw.get(section, {})
            data = body.get("data", {})
            for metric, periods in data.items():
                if isinstance(periods, dict):
                    for period, val in periods.items():
                        fv = db.tofloat(val)
                        if fv is not None:
                            metrics.append((code, section, metric, str(period), fv))
                            
        # CAGRs have no 'data' wrapper
        cagrs = raw.get("CAGRs", {})
        for metric, periods in cagrs.items():
            if isinstance(periods, dict):
                for period, val in periods.items():
                    fv = db.tofloat(val)
                    if fv is not None:
                        metrics.append((code, "CAGRs", metric, str(period), fv))

    c.executemany("INSERT OR REPLACE INTO companies VALUES(?,?,?,?,?)", companies)
    c.executemany("INSERT OR REPLACE INTO raw VALUES(?,?)", raws)
    c.executemany("INSERT OR REPLACE INTO metrics VALUES(?,?,?,?,?)", metrics)
    c.commit(); c.close()
    print(f"  loaded {len(metrics)} metrics for {len(companies)} companies")
