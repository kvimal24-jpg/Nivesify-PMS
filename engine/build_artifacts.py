import os, re, json, math
import numpy as np
from datetime import datetime, timezone
from engine import config, db, fetch_datalake, fetch_prices, fetch_macro, scoring, portfolio_engine

def slug(s): return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")

# BULLETPROOF SANITIZER: Catches Python floats, NumPy floats, and NaN/Inf
def sanitize_for_json(obj):
    if isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_for_json(v) for v in obj]
    elif isinstance(obj, (int, np.integer)):
        return int(obj)
    elif isinstance(obj, (float, np.floating)):
        f = float(obj)
        if math.isnan(f) or math.isinf(f):
            return None  # Force NaN/Inf to become JSON 'null'
        return f
    elif isinstance(obj, np.ndarray):
        return sanitize_for_json(obj.tolist())
    return obj

def write(name, obj): 
    with open(os.path.join(config.SITE_DATA, name), "w") as f:
        json.dump(sanitize_for_json(obj), f, ensure_ascii=False)

def main():
    db.init(); db.reset(); os.makedirs(config.SITE_DATA, exist_ok=True)
    print("→ Data lake"); master, mapped = fetch_datalake.download(); fetch_datalake.normalize(master, mapped)
    print("→ Prices"); prices = fetch_prices.run()
    print("→ Macro"); fetch_macro.run()

    c = db.conn()
    comps = {r["code"]: dict(r) for r in c.execute("SELECT * FROM companies")}
    sectors = sorted({v["sector"] for v in comps.values()})
    pbs = scoring.load_playbooks(); generic = pbs.get("*", {"metrics": []})
    
    mp = os.path.join(config.CACHE, "master_data.json")
    raw_master = json.load(open(mp, encoding="utf-8")) if os.path.exists(mp) else {}

    for sec in sectors:
        codes = [k for k, v in comps.items() if v["sector"] == sec]
        mdata = db.load_latest_metrics(codes)
        pb = pbs.get(sec, generic)
        sc = scoring.score_sector(codes, pb, mdata, raw_master)
        
        for code, s in zip(codes, sc):
            c.execute("INSERT OR REPLACE INTO scores VALUES(?,?,?)", (code, sec, s))
            
        def avg(path):
            vals = [scoring._val(mdata, x, path) for x in codes]
            vals = [v for v in vals if v is not None and not (isinstance(v, float) and math.isnan(v))]
            return round(sum(vals) / len(vals), 2) if vals else None
            
        priced = [comps[x] for x in codes if comps[x]["nse"] in prices]
        chgs = [prices[x["nse"]]["chg"] for x in priced if prices[x["nse"]].get("chg") is not None]
        scored = [(x, s) for x, s in zip(codes, sc) if s is not None]
        scored.sort(key=lambda t: -t[1])
        combined = {"count": len(codes), "avg_score": round(sum(s for _, s in scored) / max(1, len(scored)), 1) if scored else None,
                    "avg_roce": avg("ratios.ROCE %"), "avg_roe": avg("ratios.ROE %"),
                    "avg_pe": avg("ratios.Stock P/E"), "avg_de": avg("ratios.Debt to equity"),
                    "momentum": round(sum(chgs) / len(chgs), 2) if chgs else None,
                    "top": [{"code": x, "name": comps[x]["name"], "score": s} for x, s in scored[:10]]}
        c.execute("INSERT OR REPLACE INTO sector_text VALUES(?,?)", (sec, json.dumps(sanitize_for_json(combined))))
        sector_meta = {sec: {"slug": slug(sec), "name": sec, "playbook": pb.get("name", "Generic v1"),
                            "brief": pb.get("analyst_brief"), **combined} for sec in sectors}

    c.commit(); c.close()

    index = []
    for code, v in comps.items():
        pr = prices.get(v["nse"], {})
        srow = db.conn().execute("SELECT score FROM scores WHERE code=?", (code,)).fetchone()
        index.append({"code": code, "name": v["name"], "sector": v["sector"], "industry": v["industry"],
                      "price": pr.get("price"), "chg": pr.get("chg"), "score": srow["score"] if srow else None})
    
    write("index.json", index)
    write("sectors.json", sector_meta)
    for sec, meta in sector_meta.items():
        stocks = [x for x in index if x["sector"] == sec]
        stocks.sort(key=lambda r: r["score"] if r["score"] is not None else -1, reverse=True)
        write(f"sector__{meta['slug']}.json", {"meta": meta, "stocks": stocks})
        
    cc = db.conn()
    for code in comps:
        raw = json.loads(cc.execute("SELECT blob FROM raw WHERE code=?", (code,)).fetchone()["blob"])
        v = comps[code]; pr = prices.get(v["nse"], {})
        srow = cc.execute("SELECT score FROM scores WHERE code=?", (code,)).fetchone()
        pros = [r["text"] for r in cc.execute("SELECT text FROM pros_cons WHERE code=? AND kind='pros'", (code,))]
        cons = [r["text"] for r in cc.execute("SELECT text FROM pros_cons WHERE code=? AND kind='cons'", (code,))]
        raw.setdefault("analysis", {})["pros"] = pros; raw["analysis"]["cons"] = cons
        write(f"stock__{code}.json", {"code": code, "name": v["name"], "sector": v["sector"],
              "industry": v["industry"], "price": pr.get("price"), "chg": pr.get("chg"),
              "score": srow["score"] if srow else None, "raw": raw})
    cc.close()
    
    mc = db.conn(); macro = [dict(r) for r in mc.execute("SELECT * FROM macro")]; mc.close()
    write("macro.json", macro)
    ports = portfolio_engine.build_all({k: {**v, "price": prices.get(v["nse"], {}).get("price")} for k, v in comps.items()})
    for cid, p in ports.items(): write(f"portfolio__{cid}.json", p)
    write("meta.json", {"built_at": datetime.now(timezone.utc).isoformat(), "companies": len(comps),
                        "sectors": len(sectors), "portfolios": list(ports)})
    print(f"✓ Built {len(comps)} companies · {len(sectors)} sectors")

if __name__ == "__main__": main()
