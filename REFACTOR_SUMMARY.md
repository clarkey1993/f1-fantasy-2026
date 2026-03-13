# F1 Fantasy Scoring Refactor Summary

## What Changed

### 1. Shared Config (`f1_config.py`)

- **Single source of truth** for driver/constructor mappings used by both `app.py` and `scoring.py`.
- Contains: `DRIVER_MAP`, `DRIVER_TEAM_MAP`, `CONSTRUCTOR_MAP`, `TEAM_CONFIG`, `get_team_config()`, `app_constructor_to_fastf1()`.
- Prevents drift between UI and scoring logic.

### 2. Fantasy Starting Grid (`scoring.py`)

- **`build_fantasy_grid(results)`** builds an adjusted starting grid before driver scoring:
  - Uses official race starting positions.
  - **DNS (formation lap non-starters):** Drivers who did not pass the start line (e.g. 0 laps, "Did not start", "Withdrawn") get **no points** for the weekend and are removed from the grid; drivers below move up.
  - **Pit lane starters:** `GridPosition == 0` → 1 grid point (position 20). Drivers below their slot move up.
  - Returns `(fantasy_grid, dns_abbrs)` for use in grid points and position gain.

### 3. Driver Scoring Updates

- **Grid points:** 20 for P1, 19 for P2, down to 1 for P20 (unchanged formula, now based on fantasy grid).
- **Pit lane:** 1 grid point (position 20).
- **DNS:** 0 points for the weekend; no laps, no finishing points.
- **Position gain:** `fantasy_start - classified_finish`; only counted if positive.
- **DSQ / Excluded / Black flagged:** Grid points kept; no laps, finish, or fastest lap; **-20 points**.

### 4. Constructor Scoring

- Reorganised into `score_constructor()`:
  - -10 points per DSQ/excluded car.
  - +10 points per car that actually finishes.
  - Best finishing car: standard scale (25, 18, 15, 12, 10, 8, 6, 4, 2, 1).
- Fuzzy team matching as fallback when FastF1 team names differ.

### 5. Tie-Break Columns

Stored in the dataframe and synced to Google Sheets:

- `Driver Race Pts` – Sum of driver race-only points.
- `Constructor Race Pts` – Sum of constructor points.
- `Top Driver Score` – Highest single-driver race score.
- `Best Finish Pos` – Best classified finish among drivers (e.g. P1 = 1).

`get_league_data()` initialises these columns for older data.

### 6. App Changes

- `app.py` imports mappings from `f1_config` and no longer keeps its own copies.
- No route or template changes.

---

## Assumptions Needing Commissioner Confirmation

1. **Pit lane “original” grid position:** FastF1 uses `GridPosition == 0` for pit lane starters and does not expose their original qualifying slot. The fantasy grid assumes they occupy position 20 (1 grid point), and that other drivers are already correctly ordered. If qualifying data is needed for “drivers below move up”, that would require extra logic.

2. **DNS detection:** Treated as DNS when: (a) Status is "Did not start" or "Withdrawn", or (b) Laps completed = 0. A formation-lap retirement with 0 laps is therefore treated as DNS.

3. **Black flag:** Black-flagged drivers are scored like DSQ (grid points kept, -20, no other points).

4. **Constructor DSQ wording:** Implemented for Status containing "Disqualified" or "Excluded". If "black flag" or other wording should count for constructors, that can be added.

5. **Cadillac mapping:** For 2024 data, Cadillac maps to Williams. For 2026 data, this may need to be updated when FastF1 adds Cadillac.

---

## Files Modified

- `f1_config.py` (new)
- `scoring.py` (refactored)
- `app.py` (imports from `f1_config`, tie-break cols in `get_league_data`)
- `REFACTOR_SUMMARY.md` (this file)

---

## Preserved Behaviour

- Route names and return formats unchanged.
- `calculate_race_scores(df, year, round_name, race_payouts=None, is_test=False)` signature and return type unchanged.
- Google Sheets sync unchanged.
- Templates and UI unchanged (no tie-break display yet).
- Structure allows sprint logic to be added later without major refactors.
