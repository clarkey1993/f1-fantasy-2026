# Strict Code Review: Implementation vs Fantasy Rules

## Rule-by-Rule Verification

### 1. Adjusted fantasy starting grid

**Rule:** Build a fantasy-adjusted starting grid before scoring; handle pit lane and DNS; renumber positions.

**Implementation:** `build_fantasy_grid(results)` — `scoring.py:69-119`

| Aspect | Status | Code Reference |
|--------|--------|----------------|
| Start from official grid | Exact | Lines 76-86: reads `GridPosition` from `results` |
| Exclude DNS from grid | Exact | Lines 84-85, 96-97: `_did_not_start` → `dns_abbrs`; excluded from `active` |
| Pit lane at position 20 | Exact | Lines 102-118: pit lane in `pit_lane_drivers`, assigned `len(on_grid)+j+1` |
| Others renumbered 1–N | Exact | Lines 110-115: `on_grid` sorted by grid, assigned 1 to len(on_grid) |

**Verdict:** **Exact** — Logic matches the rule.

---

### 2. Pit lane start rule

**Rule:** Pit lane = 1 grid point. Drivers below their original slot move up.

**Implementation:** `_pit_lane_start()` — `scoring.py:46-51`; `build_fantasy_grid` — `scoring.py:102-118`

| Aspect | Status | Code Reference |
|--------|--------|----------------|
| Pit lane = 1 grid point | Exact | Fantasy pos 20 → `21-20=1` in `score_driver:149` |
| Drivers below move up | **Approximate** | See below |

**Why approximate:** The rule assumes we know the pit lane driver’s “original grid position” to move drivers below them up. FastF1 only gives `GridPosition=0` for pit lane starters. The code treats pit lane as not on the grid, assigns positions 1–19 to the 19 on-grid drivers, and pit lane as 20. That effectively moves everyone behind the vacated slot up, but only if FastF1’s grid order is correct. We cannot verify the vacated slot without qualifying data.

**Verdict:** **Approximate** — Behaviour is correct for the data we have; it cannot fully follow the rule without original qualifying position.

---

### 3. Formation-lap non-starter rule

**Rule:** Did not pass start line → NO points; drivers below move up.

**Implementation:** `_did_not_start()` — `scoring.py:36-43`; `build_fantasy_grid` — `scoring.py:84-85, 96-97`; `score_driver` — `scoring.py:126-128`

| Aspect | Status | Code Reference |
|--------|--------|----------------|
| No points for weekend | Exact | `score_driver:126-128` returns `0, 0, None` for DNS |
| Drivers below move up | Exact | DNS excluded from `active`; on-grid renumbered |

**DNS detection logic (`scoring.py:36-43`):**
```python
if 'did not start' in s or 'withdrawn' in s: return True
if laps == 0: return True
```

**Why potentially approximate:** Any driver with 0 laps is treated as DNS. A driver who crosses the line but is incorrectly recorded as 0 laps would wrongly score 0. Status checks are limited to “did not start” and “withdrawn”; other FIA status strings might not be covered. The rule does not explicitly define every status; reliance on `laps == 0` is a heuristic.

**Verdict:** **Approximate** — Handles the common cases; edge cases depend on FastF1 laps/status accuracy.

---

### 4. Grid points

**Rule:** 20 for P1, 19 for P2, down to 1 for P20.

**Implementation:** `score_driver` — `scoring.py:141-152`

```python
grid_pts = max(0, 21 - grid_pos)
pts += grid_pts
```

**Verdict:** **Exact** — Correct mapping.

---

### 5. Lap points

**Rule:** 1 point per lap completed.

**Implementation:** `score_driver` — `scoring.py:130-138, 159-161`

| Aspect | Status | Code Reference |
|--------|--------|----------------|
| Lap count from results | Exact | Line 130: `laps = safe_int(d.get('Laps'), 0)` |
| Fallback from session.laps | Exact | Lines 132-137: `session.laps.pick_driver(abbr)` |
| Fallback when finished but 0 laps | Exact | Lines 137-138: if `_finished` and laps==0, use `max_laps` |
| Add laps to points | Exact | Lines 159-161 |

**Verdict:** **Exact** — Logic matches the rule.

---

### 6. Positive position gain only

**Rule:** 1 bonus point per position gained; only if gain > 0.

**Implementation:** `score_driver` — `scoring.py:165-171`

```python
gain = grid_pos - finish
if gain > 0:
    pts += gain
```

**Verdict:** **Exact** — Only positive gains are scored.

---

### 7. Finishing points

**Rule:** P1=25, P2=18, …, P10=1; only if driver crossed the line.

**Implementation:** `score_driver` — `scoring.py:163-173`; `_finished()` — `scoring.py:30-33`

| Aspect | Status | Code Reference |
|--------|--------|----------------|
| Scale 25,18,15,12,10,8,6,4,2,1 | Exact | `FINISH_POINTS` dict, line 14 |
| Only if crossed line | Exact | Gated by `if not _finished(status): return` at 163-164 |
| Uses ClassifiedPosition | Exact | Line 165: `safe_int(d.get('ClassifiedPosition'), 999)` |

**Verdict:** **Exact** — Correct scale and condition.

---

### 8. Fastest lap

**Rule:** 25 points for fastest lap.

**Implementation:** `score_driver` — `scoring.py:175-178`; `calculate_race_scores` — `scoring.py:250-254`

| Aspect | Status | Code Reference |
|--------|--------|----------------|
| Only if driver finished | Exact | Fastest lap added after `_finished` check (163-164) |
| 25 points | Exact | Line 176 |
| Driver comparison | Exact | `abbr == fastest_lap_abbr`; FastF1 Laps `Driver` = 3-letter code |

**Verdict:** **Exact** — Logic matches the rule.

---

### 9. DSQ / excluded / black flag deductions

**Rule (driver):** Grid points stand; no other points; −20.

**Implementation:** `_disqualified()` — `scoring.py:55-57`; `score_driver` — `scoring.py:154-157`

```python
if _disqualified(status):
    pts -= 20
    race_pts -= 20
    return pts, race_pts, None  # After grid points, before laps/finish/fl
```

**Rule (constructor):** −10 per DSQ/excluded car.

**Implementation:** `score_constructor` — `scoring.py:198-200`

```python
dq_cars = t_data[t_data['Status'].str.contains('Disqualified|Excluded', na=False, case=False)]
pts -= len(dq_cars) * 10
```

**Why constructor is approximate:** Rule mentions “disqualified or excluded” only. Code does not check “black flag”. If a constructor car is black-flagged, it would not be penalised. Driver black flag is handled; constructor rule does not mention it.

**Verdict (driver):** **Exact** — DSQ, excluded, black flag all handled.  
**Verdict (constructor):** **Exact** for DSQ/excluded; **Not implemented** for black flag (rule is silent).

---

### 10. Constructor 10 points per finisher

**Rule:** 10 points for each car that actually finishes.

**Implementation:** `score_constructor` — `scoring.py:201-206`

```python
for _, car in t_data.iterrows():
    if _finished(car['Status']):
        finishers.append(car)
pts += len(finishers) * 10
```

**Verdict:** **Exact** — Uses same `_finished` logic as drivers.

---

### 11. Constructor best-car finish points only

**Rule:** Constructor finishing points only from highest placed finishing car.

**Implementation:** `score_constructor` — `scoring.py:207-210`

```python
best_pos = min(safe_int(c.get('ClassifiedPosition'), 999) for c in finishers)
pts += FINISH_POINTS.get(best_pos, 0)
```

**Verdict:** **Exact** — Only best finishing car counts.

---

### 12. Tie-break data capture

**Rule:** Store data for tie-break use.

**Implementation:** `calculate_race_scores` — `scoring.py:270-272, 326-331`

| Column | Status | Code Reference |
|--------|--------|----------------|
| Driver Race Pts | Exact | Lines 310, 327 |
| Constructor Race Pts | Exact | Lines 319, 328 |
| Top Driver Score | Exact | Lines 311-312, 329 |
| Best Finish Pos | Exact | Lines 313-314, 330 |

**Verdict:** **Exact** — All four tie-break columns are stored.

---

### 13. Tie-break ranking application

**Rule:** Use tie-break rules when ranking tied managers.

**Implementation:** `calculate_race_scores` — `scoring.py:345`; `app.py` leaderboard

```python
df = df.sort_values(by=['Current Score', 'Total Winnings'], ascending=False)
```

**Verdict:** **Not implemented** — Sorting uses only `Current Score` and `Total Winnings`. Tie-break columns are stored but not used for ranking.

---

## Logic That Could Produce Wrong Scoring

1. **`_did_not_start` + laps fallback (`scoring.py:130-138`)**  
   If FastF1 `Laps` is 0 but `session.laps.pick_driver()` finds laps, we use that. If `Laps` is wrong and `session.laps` is empty, we might treat a finisher as DNS or the opposite.

2. **`session.laps.pick_driver` deprecated**  
   `scoring.py:133` uses `pick_driver`, which is deprecated. Future FastF1 versions may remove it and break lap fallback.

3. **Constructor fuzzy match (`scoring.py:191`)**  
   `results['TeamName'].str.contains(official_team, case=False)` can over-match. Example: `"Alpine"` matches `"Alpine F1 Team"` (correct) but could match any team name containing “Alpine” if such a team existed.

4. **`fantasy_grid.get(abbr, 20)` fallback (`scoring.py:141-144`)**  
   If a driver is in `results` but not in `fantasy_grid` (e.g. data inconsistency), they get grid position 20 and 1 grid point. That may be wrong for reserve drivers or late additions.

5. **`pick_fastest()` failure**  
   If `pick_fastest()` throws (e.g. no valid laps), `fastest_lap_abbr` stays `None`. `abbr == None` is always false, so no one gets fastest lap. Acceptable, but no explicit handling.

6. **`best_finish_positions` 999 sentinel (`scoring.py:286, 330`)**  
   When all drivers DNF, `best_finish` stays 999. That is stored; any tie-break logic must treat 999 as “no classified finish”.

---

## Naming and Mapping Risks

### Fantasy driver names ↔ FastF1 abbreviations

| Risk | Location | Detail |
|------|----------|--------|
| Spelling mismatch | `DRIVER_MAP` keys vs `Picks` | `"Carlos Sainz Jnr"` in map; `"Carlos Sainz"` from sheet → no match → 0 points. |
| New driver missing | `f1_config.py:6-15` | 2026 rookies or mid-season changes may lack entries. |
| Abbreviation change | FastF1 vs `DRIVER_MAP` | e.g. Jack Doohan `"DOO"` in config; FastF1 might use different code. |

### Team names

| Risk | Location | Detail |
|------|----------|--------|
| `app_constructor_to_fastf1` order | `f1_config.py:70-76` | Iterates `CONSTRUCTOR_MAP`; first match wins. `"Red Bull"` in `"Aston Martin Red Bull"` would not match if “Aston Martin” came first. |
| Cadillac placeholder | `f1_config.py:36` | `"Cadillac"` → `"Williams"` for 2024. In 2026, FastF1 may use `"Cadillac"`; mapping may need update. |
| Fuzzy match breadth | `scoring.py:191` | `"Williams"` in `"Williams F1 Team"` is fine; any substring could cause false positives. |

### App vs scoring

| Risk | Detail |
|------|--------|
| Shared config | `f1_config` is used by both; main risk is new drivers/teams only added in one place. |
| Parse consistency | `_parse_picks` (scoring) and `parse_picks` (app) both handle smart quotes; formats must stay compatible. |

---

## Functions and Responsibilities

| Responsibility | Function | File:Line |
|----------------|----------|-----------|
| Build fantasy grid | `build_fantasy_grid(results)` | `scoring.py:69-119` |
| Score a single driver | `score_driver(d, fantasy_grid, dns_abbrs, fastest_lap_abbr, max_laps, session, abbr)` | `scoring.py:122-180` |
| Score a constructor | `score_constructor(pick, results, session)` | `scoring.py:183-211` |
| Main scoring loop | `calculate_race_scores(df, year, round_name, race_payouts, is_test)` | `scoring.py:214-354` |
| Pit lane check | `_pit_lane_start(grid_pos)` | `scoring.py:46-51` |
| DNS check | `_did_not_start(status, laps)` | `scoring.py:36-43` |
| Finished check | `_finished(status)` | `scoring.py:30-33` |
| DSQ check | `_disqualified(status)` | `scoring.py:55-57` |

---

## Top 3 Recommended Fixes

### 1. Replace deprecated `pick_driver` (high)

**Issue:** `session.laps.pick_driver(abbr)` is deprecated and may be removed.

**Change:** Use `session.laps.pick_drivers(abbr)` and adjust for the new return type (e.g. `Laps` instead of `Laps` for one driver).

**Location:** `scoring.py:133`

---

### 2. Add type-normalisation for fastest-lap comparison (medium)

**Issue:** `fastest_lap_abbr` comes from `session.laps.pick_fastest()['Driver']`; indexing may return non-string types.

**Change:** Normalise to string before comparison, e.g.:
```python
fastest_lap_abbr = str(fastest_lap_abbr).strip() if fastest_lap_abbr is not None else None
```
and use the same normalisation for `abbr` when comparing.

**Location:** `scoring.py:252`, `scoring.py:175`

---

### 3. Make constructor fuzzy match safer (medium)

**Issue:** `str.contains(official_team)` can over-match and match the wrong team.

**Change:** Prefer word-boundary or exact phrase matching, or only fall back to fuzzy when the exact name is a known substring (e.g. “Kick Sauber” in “Kick Sauber F1 Team”). Alternatively, restrict fuzzy match to known patterns instead of a generic substring check.

**Location:** `scoring.py:191`
