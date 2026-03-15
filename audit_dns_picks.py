import ast
import pandas as pd

df = pd.read_csv("league_data.csv")

# Check both ASCII and Unicode (Hülkenberg) variants
drivers_hulkenberg = ["Nico Hulkenberg", "Nico Hülkenberg"]
driver_piastri = "Oscar Piastri"

results = []

for _, row in df.iterrows():
    name = row.get("Name")
    picks_raw = row.get("Picks")

    try:
        picks = ast.literal_eval(picks_raw) if isinstance(picks_raw, str) else picks_raw
    except Exception:
        picks = []

    has_hulkenberg = any(h in picks for h in drivers_hulkenberg)
    has_piastri = driver_piastri in picks

    results.append({
        "name": name,
        "has_hulkenberg": has_hulkenberg,
        "has_piastri": has_piastri
    })

print("\nDriver discrepancy audit\n")

for r in results:
    if r["has_hulkenberg"] or r["has_piastri"]:
        print(f"{r['name']}: HUL={r['has_hulkenberg']}  PIA={r['has_piastri']}")
