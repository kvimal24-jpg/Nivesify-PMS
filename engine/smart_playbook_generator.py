import sqlite3
import json
import os

print("  Scanning SQLite database for Financial Services metrics...")
conn = sqlite3.connect('cache/pms.sqlite')
cur = conn.cursor()

# Get all unique metric paths (section.metric) actually present for Financial Services
cur.execute("""
    SELECT DISTINCT section, metric 
    FROM metrics 
    WHERE code IN (SELECT code FROM companies WHERE sector = 'Financial Services')
""")
available = {f"{row[0]}.{row[1]}" for row in cur.fetchall()}
print(f"  Found {len(available)} unique data points for Financial Services.")

# Define our institutional targets and their potential Screener.in aliases
targets = [
    {"ideal": "Net Interest Margin (NIM)", "aliases": ["ratios.NIM %", "ratios.NIM"], "direction": "higher", "weight": 3},
    {"ideal": "CASA Ratio", "aliases": ["ratios.CASA %", "ratios.CASA"], "direction": "higher", "weight": 3},
    {"ideal": "Gross NPA Ratio", "aliases": ["ratios.GNPA %", "ratios.Gross NPA %"], "direction": "lower", "weight": 3},
    {"ideal": "Net NPA Ratio", "aliases": ["ratios.NNPA %", "ratios.Net NPA %"], "direction": "lower", "weight": 3},
    {"ideal": "Provision Coverage Ratio", "aliases": ["ratios.Provision coverage ratio", "ratios.PCR %", "ratios.Provision Coverage Ratio %"], "direction": "higher", "weight": 3},
    {"ideal": "Return on Assets (RoA)", "aliases": ["ratios.ROA %", "ratios.Return on assets %"], "direction": "higher", "weight": 3},
    {"ideal": "Return on Equity (RoE)", "aliases": ["ratios.ROE %", "ratios.Return on equity %"], "direction": "higher", "weight": 3},
    {"ideal": "Capital Adequacy Ratio", "aliases": ["ratios.CRAR %", "ratios.CAR %", "ratios.Capital adequacy ratio %"], "direction": "higher", "weight": 3},
    {"ideal": "Cost-to-Income Ratio", "aliases": ["ratios.Cost to income %", "ratios.Cost to income ratio %"], "direction": "lower", "weight": 2},
    {"ideal": "Debt to Equity", "aliases": ["ratios.Debt to equity"], "direction": "lower", "weight": 2},
    {"ideal": "Promoter Holding", "aliases": ["ratios.Promoter holding"], "direction": "higher", "weight": 1},
    {"ideal": "Pledged Shares", "aliases": ["ratios.Pledged %"], "direction": "lower", "weight": 3},
    {"ideal": "Stock P/E", "aliases": ["ratios.Stock P/E", "ratios.P/E"], "direction": "lower", "weight": 2},
    {"ideal": "Price to Book", "aliases": ["ratios.Price to book", "ratios.P/B"], "direction": "lower", "weight": 2},
    {"ideal": "Sales Growth CAGR", "aliases": ["CAGRs.Sales", "CAGRs.Income"], "direction": "higher", "weight": 2},
    {"ideal": "Profit Growth CAGR", "aliases": ["CAGRs.Profit", "CAGRs.Net Profit"], "direction": "higher", "weight": 2},
]

metrics_json = []
for t in targets:
    matched_path = next((alias for alias in t["aliases"] if alias in available), None)
    
    if matched_path:
        metrics_json.append({
            "metric_name": t["ideal"],
            "path": matched_path,
            "direction": t["direction"],
            "weight": t["weight"]
        })
        print(f"    ✅ Mapped {t['ideal']} -> {matched_path}")
    else:
        print(f"    ⚠️ Skipped {t['ideal']} (not found in scraped data)")

playbook = {
    "match": {"sector": "Financial Services"},
    "name": "Financial Services v1.0 - Institutional Grade",
    "analyst_brief": "The Indian financial services ecosystem acts as the central transmission engine for economic expansion. The primary operating paradigm relies on accumulating low-cost CASA deposits and deploying this capital into credit assets. Macro tailwinds are anchored by sustained credit growth outstripping nominal GDP, historically low systemic gross NPAs, and robust capitalization ratios. Moats are forged through granular deposit franchises and proprietary underwriting algorithms.",
    "metrics": metrics_json,
    "red_flags": [
        {"metric": "Gross NPA", "condition": "> 5.0%", "severity": "Critical", "reason": "Systemic asset quality deterioration."},
        {"metric": "Pledged Shares", "condition": "> 10.0%", "severity": "Critical", "reason": "Promoter stress indicator."},
        {"metric": "Capital Adequacy Ratio", "condition": "< 13.0%", "severity": "High", "reason": "Below RBI comfort zone."}
    ]
}

os.makedirs('playbooks', exist_ok=True)
with open('playbooks/Financial Services.json', 'w') as f:
    json.dump(playbook, f, indent=2)

print(f"\n✅ Playbook generated successfully with {len(metrics_json)} validated metrics!")
