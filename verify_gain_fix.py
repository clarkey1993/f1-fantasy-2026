"""Sanity check: Verstappen +12, Gasly +2, Albon +1 after finisher-only gain fix."""
import fastf1
from scoring import build_fantasy_grid, _build_finisher_pos_map, get_team_scoring_breakdown

fastf1.Cache.enable_cache('f1_cache')
session = fastf1.get_session(2026, 'Australia', 'R')
session.load(telemetry=False, weather=False)
results = session.results

fantasy_grid, dns_abbrs = build_fantasy_grid(results)
finisher_pos_map = _build_finisher_pos_map(results)

# Verstappen: grid 20 (fantasy), finished 8th among finishers
# Gasly: grid 14 (fantasy), finished 12th among finishers
# Albon: grid 15 (fantasy), finished 14th among finishers
for abbr in ['VER', 'GAS', 'ALB']:
    grid = fantasy_grid.get(abbr)
    finish = finisher_pos_map.get(abbr)
    gain = (grid - finish) if (grid and finish) else None
    print(f"{abbr}: fantasy_grid={grid}, finisher_pos={finish}, gain={gain}")

# Get breakdown for a team that has VER, GAS, ALB
# Use Andy Coates or similar - pick a team with these drivers
out = get_team_scoring_breakdown(
    ['Verstappen', 'Gasly', 'Albon', 'Norris', 'Hamilton', 'Leclerc', 'Russell', 'Antonelli', 'Bearman', 'Lawson',
     'Mercedes', 'Ferrari', 'McLaren', 'Red Bull', 'Alpine', 'Williams'],
    2026, 'Australia'
)
if 'error' in out:
    print("Error:", out['error'])
else:
    for d in out.get('driver_breakdowns', []):
        if d.get('abbr') in ('VER', 'GAS', 'ALB'):
            print(f"  {d['abbr']}: gain_pts={d.get('gain_pts')}, finish_pos={d.get('finish_pos')}")
