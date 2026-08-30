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
    if "." not in path: return None
    sec, met = path.split(".", 1)
    return mdata.get(code, {}).get((sec, met))

def score_sector(codes, playbook, mdata):
    layers = []
    for m in playbook.get("metrics", []):
        pairs = [(i, _val(mdata, c, m["path"])) for i, c in enumerate(codes)]
        pairs = [(i, v) for i, v in pairs if v is not None]
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
