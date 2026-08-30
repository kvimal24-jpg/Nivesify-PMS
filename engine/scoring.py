import os, json, glob
from engine import config

def load_playbooks():
    pbs = {}
    for f in glob.glob(os.path.join(config.PLAYBOOKS, "*.json")):
        try:
            pb = json.load(open(f, encoding="utf-8"))
            pbs[pb.get("match", {}).get("sector", "*")] = pb
        except Exception as e: print("  playbook err:", f, e)
    return pbs

def _val(mdata, code, path):
    if path is None: return None
    if "." not in path: return None
    sec, met = path.split(".", 1)
    return mdata.get(code, {}).get((sec, met))

def calculate_missing_metrics(code, raw_data):
    calculated = {}
    pl = raw_data.get("profitLoss", {})
    bs = raw_data.get("balanceSheet", {})
    
    def get_latest(section, key_part):
        for key, val in section.items():
            if key_part.lower() in key.lower() and isinstance(val, dict):
                years = [y for y in val.keys() if y not in ["", "TTM", "x", "X"]]
                if years:
                    try: return float(val[years[-1]])
                    except Exception: return None
        return None

    int_earned = get_latest(pl, "interest earned") or get_latest(pl, "income")
    int_exp = get_latest(pl, "interest expended") or get_latest(pl, "expense")
    other_inc = get_latest(pl, "other income") or 0
    op_exp = get_latest(pl, "operating expense")
    provisions = get_latest(pl, "provision")
    advances = get_latest(bs, "advances")
    total_deposits = get_latest(bs, "deposit")
    
    # NIM
    if int_earned and int_exp and advances and advances > 0:
        calculated[("calc", "NIM")] = round(((int_earned - int_exp) / advances) * 100, 2)
    
    # Cost-to-Income
    if int_earned and op_exp:
        total_inc = int_earned + (other_inc if other_inc else 0)
        if total_inc > 0:
            calculated[("calc", "Cost to Income")] = round((op_exp / total_inc) * 100, 2)
    
    # Credit Cost (Provisions / Advances)
    if provisions and advances and advances > 0:
        calculated[("calc", "Credit Cost")] = round((provisions / advances) * 100, 2)
    
    # PCR approximation (if we can find both)
    gnma = get_latest(bs, "npa")
    if provisions and gnma and gnma > 0:
        calculated[("calc", "PCR")] = round((provisions / gnma) * 100, 2)
    
    # Fee Income Ratio
    if other_inc and int_earned:
        total_inc = int_earned + other_inc
        if total_inc > 0:
            calculated[("calc", "Fee Income Ratio")] = round((other_inc / total_inc) * 100, 2)
    
    return calculated

def score_sector(codes, playbook, mdata, raw_map):
    layers = []
    for m in playbook.get("metrics", []):
        if not m.get("scorable", False):
            continue  # Skip qualitative metrics for scoring
        pairs = []
        metric_name = m.get("metric_name") or m.get("name") or "Unknown"
        
        for i, c in enumerate(codes):
            v = _val(mdata, c, m.get("path"))
            if v is None and raw_map.get(c) and m.get("path", "").startswith("calc."):
                calc = calculate_missing_metrics(c, raw_map[c])
                calc_key = ("calc", metric_name)
                if calc_key in calc:
                    v = calc[calc_key]
            if v is not None:
                pairs.append((i, v))
                
        if not pairs: continue
        pairs.sort(key=lambda x: x[1])
        n = max(len(pairs) - 1, 1)
        sc = {i: (r / n) * 100 for r, (i, _) in enumerate(pairs)}
        if m.get("direction") == "lower": sc = {i: 100 - v for i, v in sc.items()}
        layers.append((m.get("weight", 1), sc))
        
    out = []
    for i in range(len(codes)):
        tot = wsum = 0
        for w, sc in layers:
            if i in sc: tot += w * sc[i]; wsum += w
        out.append(round(tot / wsum, 1) if wsum else None)
    return out
