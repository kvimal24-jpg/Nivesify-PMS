import os, re, json, math
import numpy as np
from datetime import datetime, timezone
from engine import config, db, fetch_datalake, fetch_prices, fetch_macro, scoring, portfolio_engine

def slug(s): return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")

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
            return None
        return f
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
    
    sector_meta = {}
    for sec in sectors:
        print(f"  Scoring {sec}...")
        codes = [k for k, v in comps.items() if v["sector"] == sec]
        
        # DYNAMIC SCORING: Find common metrics and score them automatically
        common_metrics = scoring.get_common_metrics(sec)
        
        # Define direction for scoring
        metrics_to_score = []
        for s, m in common_metrics:
            if "debt" in m.lower() or "pe" in m.lower() or "price to book" in m.lower() or "gnpa" in m.lower() or "nnpa" in m.lower() or "pledged" in m.lower():
                direction = "lower"
            else:
                direction = "higher"
            metrics_to_score.append((s, m, direction))
            
        scores = scoring.score_sector(codes, metrics_to_score)
        
        for code, s in scores.items():
            c.execute("INSERT OR REPLACE INTO scores VALUES(?,?,?)", (code, sec, s))
            
        # Sector stats
        def avg(section, metric):
            vals = []
            for code in codes:
                row = c.execute("SELECT value FROM metrics WHERE code=? AND section=? AND metric=? AND period='TTM'", (code, section, metric)).fetchone()
                if not row:
                    row = c.execute("SELECT value FROM metrics WHERE code=? AND section=? AND metric=? AND period NOT IN ('TTM','x','X','') ORDER BY period DESC LIMIT 1", (code, section, metric)).fetchone()
                if row and row["value"]: vals.append(row["value"])
            return round(sum(vals)/len(vals), 2) if vals else None
            
        priced = [comps[x] for x in codes if comps[x]["nse"] in prices]
        chgs = [prices[x["nse"]]["chg"] for x in priced if prices[x["nse"]].get("chg") is not None]
        
        scored_list = [(x, scores[x]) for x in codes if scores.get(x) is not None]
        scored_list.sort(key=lambda t: -t[1])
        
        combined = {
            "count": len(codes), 
            "avg_score": round(sum(s for _, s in scored_list) / max(1, len(scored_list)), 1) if scored_list else None,
            "avg_roce": avg("ratios", "ROCE %"), 
            "avg_roe": avg("ratios", "ROE %"),
            "avg_pe": avg("ratios", "Stock P/E"), 
            "avg_de": avg("ratios", "Debt to equity"),
            "momentum": round(sum(chgs) / len(chgs), 2) if chgs else None,
            "top": [{"code": x, "name": comps[x]["name"], "score": s} for x, s in scored_list[:10]]
        }
        
        # Store sector meta
        sector_meta[sec] = {
            "slug": slug(sec), "name": sec,
            "playbook": f"Dynamic {sec} v2.0",
            "brief": f"Automatically scored using {len(metrics_to_score)} common metrics across {len(codes)} companies.",
            "metrics": [{"metric_name": m, "path": f"{s}.{m}"} for s,m in common_metrics],
            **combined
        }

    c.commit(); c.close()

    # Write files
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
        
    # Stock details
    cc = db.conn()
    for code in comps:
        raw = json.loads(cc.execute("SELECT blob FROM raw WHERE code=?", (code,)).fetchone()["blob"])
        v = comps[code]; pr = prices.get(v["nse"], {})
        srow = cc.execute("SELECT score FROM scores WHERE code=?", (code,)).fetchone()
        write(f"stock__{code}.json", {"code": code, "name": v["name"], "sector": v["sector"],
              "industry": v["industry"], "price": pr.get("price"), "chg": pr.get("chg"),
              "score": srow["score"] if srow else None, "raw": raw})
    cc.close()
    
    # Macro
    mc = db.conn(); macro = [dict(r) for r in mc.execute("SELECT * FROM macro")]; mc.close()
    write("macro.json", macro)
    
    # Portfolios
    ports = portfolio_engine.build_all({k: {**v, "price": prices.get(v["nse"], {}).get("price")} for k, v in comps.items()})
    for cid, p in ports.items(): write(f"portfolio__{cid}.json", p)
    
    write("meta.json", {"built_at": datetime.now(timezone.utc).isoformat(), "companies": len(comps),
                        "sectors": len(sectors), "portfolios": list(ports)})
    print(f"✓ Built {len(comps)} companies · {len(sectors)} sectors")

if __name__ == "__main__": main()
