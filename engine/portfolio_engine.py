import os, json, glob
from datetime import datetime, date
from engine import config, db

def xirr(cfs):
    if len(cfs) < 2: return None
    d0 = min(d for d, _ in cfs)
    def npv(r): return sum(a * (1 + r) ** (-(d - d0).days / 365.25) for d, a in cfs)
    lo, hi = -0.9, 10.0
    try:
        if npv(lo) * npv(hi) > 0: return None
    except Exception: return None
    for _ in range(80):
        mid = (lo + hi) / 2
        if npv(lo) * npv(mid) <= 0: hi = mid
        else: lo = mid
    return round((lo + hi) / 2 * 100, 2)

def build_all(company_map):
    out = {}
    for hf in glob.glob(os.path.join(config.PORTFOLIOS, "*", "holdings.json")):
        cid = os.path.basename(os.path.dirname(hf))
        data = json.load(open(hf, encoding="utf-8"))
        pos, invested, cfs = {}, 0, []
        c = db.conn()
        for t in data.get("transactions", []):
            c.execute("INSERT INTO transactions VALUES(?,?,?,?,?,?)",
                      (cid, t["date"], str(t["code"]).zfill(6), t["type"], t["qty"], t["price"]))
        c.commit(); c.close()
        for t in data.get("transactions", []):
            code = str(t["code"]).zfill(6); d = datetime.strptime(t["date"], "%Y-%m-%d").date()
            p = pos.setdefault(code, {"qty": 0, "cost": 0})
            sign = 1 if t["type"] == "buy" else -1
            p["qty"] += sign * t["qty"]; p["cost"] += sign * t["qty"] * t["price"]
            invested += sign * t["qty"] * t["price"]; cfs.append((d, -sign * t["qty"] * t["price"]))
        holdings, total, alloc = [], 0, {}
        for code, p in pos.items():
            if p["qty"] <= 0: continue
            r = company_map.get(code, {})
            val = p["qty"] * (r.get("price") or 0); total += val
            sec = r.get("sector", "Unknown"); alloc[sec] = alloc.get(sec, 0) + val
            holdings.append({"code": code, "name": r.get("name", code), "sector": sec, "qty": p["qty"],
                             "avg": round(p["cost"] / p["qty"], 1), "price": r.get("price"),
                             "value": round(val, 1), "pnl": round(val - p["cost"], 1),
                             "pnl_pct": round((val - p["cost"]) / p["cost"] * 100, 1) if p["cost"] else None})
        cfs.append((date.today(), total))
        alloc_pct = {k: round(v / total * 100, 1) for k, v in sorted(alloc.items(), key=lambda x: -x[1])} if total else {}
        warnings = [f"{k} weight {v}% breaches 35% sector mandate" for k, v in alloc_pct.items() if v > 35]
        warnings += [f"{h['name']} is {round(h['value']/total*100,1)}% of portfolio (>25% single-stock limit)"
                     for h in holdings if total and h["value"] / total > 0.25]
        out[cid] = {"client": data.get("name", cid), "invested": round(invested, 1), "current": round(total, 1),
                    "pnl": round(total - invested, 1),
                    "pnl_pct": round((total - invested) / invested * 100, 1) if invested else None,
                    "xirr": xirr(cfs), "allocation": alloc_pct,
                    "holdings": sorted(holdings, key=lambda h: -h["value"]), "warnings": warnings}
    return out
