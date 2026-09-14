from engine import db

def score_sector(codes, metrics_to_score):
    """
    metrics_to_score: list of tuples like [("ratios", "ROCE %", "higher")]
    """
    c = db.conn()
    layers = []
    
    for section, metric, direction in metrics_to_score:
        pairs = []
        # Get the latest value for each code (prioritize TTM, then latest year)
        for code in codes:
            row = c.execute("SELECT value FROM metrics WHERE code=? AND section=? AND metric=? AND period='TTM'", (code, section, metric)).fetchone()
            if not row:
                row = c.execute("""
                    SELECT value FROM metrics 
                    WHERE code=? AND section=? AND metric=? AND period NOT IN ('TTM', 'x', 'X', '')
                    ORDER BY period DESC LIMIT 1
                """, (code, section, metric)).fetchone()
            
            if row and row["value"] is not None:
                pairs.append((code, row["value"]))
                
        if not pairs: continue
        
        # Rank them 0-100 relative to peers
        pairs.sort(key=lambda x: x[1])
        n = max(len(pairs) - 1, 1)
        sc = {code: (r / n) * 100 for r, (code, _) in enumerate(pairs)}
        if direction == "lower":
            sc = {code: 100 - v for code, v in sc.items()}
            
        layers.append(sc)
        
    c.close()
    
    # Average the layers
    out = {}
    for code in codes:
        tot = count = 0
        for sc in layers:
            if code in sc:
                tot += sc[code]
                count += 1
        out[code] = round(tot / count, 1) if count else None
        
    return out

def get_common_metrics(sector):
    """Finds metrics that exist for >70% of companies in a sector"""
    c = db.conn()
    codes = [r["code"] for r in c.execute("SELECT code FROM companies WHERE sector=?", (sector,))]
    if not codes: return []
    
    metric_counts = {}
    for code in codes:
        rows = c.execute("""
            SELECT DISTINCT section, metric FROM metrics 
            WHERE code=? AND period NOT IN ('TTM', 'x', 'X', '')
        """, (code,))
        for r in rows:
            key = (r["section"], r["metric"])
            metric_counts[key] = metric_counts.get(key, 0) + 1
            
    threshold = len(codes) * 0.7
    common = [k for k, v in metric_counts.items() if v >= threshold]
    
    # Filter for the most important financial metrics to avoid clutter
    important = []
    for sec, met in common:
        if sec == "ratios":
            if any(x in met.lower() for x in ["roce", "roe", "roa", "p/e", "stock p/e", "debt", "price to book", "p/b", "gnpa", "nnpa", "crar", "car", "casa", "nim", "promoter", "pledged"]):
                important.append((sec, met))
        elif sec == "CAGRs":
            if any(x in met.lower() for x in ["sales", "profit"]):
                important.append((sec, met))
                
    c.close()
    return important
