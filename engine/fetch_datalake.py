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
    companies, metrics, proscons, raws = [], [], [], []
    for _, row in mapped.iterrows():
        code = row["BSE_Code"]; raw = master.get(code)
        if not raw: continue
        companies.append((code, row["Company_Name"], row["Sector"], row["Industry"], str(row["NSE_Code"])))
        raws.append((code, json.dumps(raw)))
        
        for kind in ("pros", "cons"):
            for t in ((raw.get("analysis") or {}).get(kind) or []):
                proscons.append((code, kind, str(t)))
                
        for section, body in raw.items():
            if section in ("analysis", "documents", "CompanyName") or not isinstance(body, dict): continue
            
            if "data" in body and isinstance(body["data"], dict):
                metrics_dict = body["data"]
            elif section == "CAGRs":
                metrics_dict = body
            else:
                continue
                
            for metric, val in metrics_dict.items():
                if isinstance(val, dict):
                    latest = None
                    # Store all valid periods
                    for period, v in val.items():
                        fv = db.tofloat(v)
                        if fv is not None:
                            metrics.append((code, section, metric, str(period), fv))
                            latest = fv
                            
                    # FIX: Prioritize TTM for "latest"
                    if "TTM" in val:
                        fv_ttm = db.tofloat(val["TTM"])
                        if fv_ttm is not None:
                            latest = fv_ttm
                            
                    # CRITICAL: Insert the 'latest' tag so the engine can find it
                    if latest is not None:
                        metrics.append((code, section, metric, "latest", latest))
                else:
                    fv = db.tofloat(val)
                    if fv is not None:
                        metrics.append((code, section, metric, "latest", fv))
                        
    c = db.conn()
    c.executemany("INSERT OR REPLACE INTO companies VALUES(?,?,?,?,?)", companies)
    c.executemany("INSERT OR REPLACE INTO raw VALUES(?,?)", raws)
    c.executemany("INSERT OR REPLACE INTO pros_cons VALUES(?,?,?)", proscons)
    c.executemany("INSERT OR REPLACE INTO metrics VALUES(?,?,?,?,?)", metrics)
    c.commit(); c.close()
    print(f"  loaded {len(metrics)} metrics for {len(companies)} companies")
