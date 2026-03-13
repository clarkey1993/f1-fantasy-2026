# F1 Fantasy Scoring – Rule-by-Rule Audit

## 1. Fully Implemented ✅

| Rule | Implementation | Evidence |
|------|----------------|----------|
| Grid points 20→1 for P1–P20 | `max(0, 21 - grid_pos)` using fantasy grid | `scoring.py:149-152` |
| Pit lane = 1 grid point | Pit lane assigned position 20 in fantasy grid | `scoring.py:117-118` |
| Formation lap non-starter = NO points | Early return for `abbr in dns_abbrs` | `scoring.py:126-128` |
| 1 point per lap completed | `pts += laps` | `scoring.py:159-161` |
| Position gain only if positive | `if gain > 0: pts += gain` | `scoring.py:166-171` |
| Finishing points P1=25…P10=1 | `FINISH_POINTS` dict | `scoring.py:13-14, 172-173` |
| Finishing points only if crossed line | Guarded by `_finished(status)` | `scoring.py:163-164` |
| Fastest lap = 25 pts | Added after finish check | `scoring.py:175-178` |
| DSQ: grid stands, -20, no other points | Early return after grid + penalty | `scoring.py:154-157` |
| Constructor 10 pts per finishing car | `pts += len(finishers) * 10` | `scoring.py:205-206` |
| Constructor best car finish points | `best_pos = min(...)` over finishers | `scoring.py:207-210` |
| Constructor -10 per DSQ/excluded car | `pts -= len(dq_cars) * 10` | `scoring.py:198-200` |
| DNS drivers removed from grid; others move up | DNS excluded from `active`; on-grid renumbered 1–N | `scoring.py:96-98, 100-117` |
| Pit lane at back; on-grid drivers renumbered | Pit lane in `pit_lane_drivers`; `on_grid` gets 1..N | `scoring.py:102-118` |
| Shared driver/constructor mappings | `f1_config.py` used by both `app.py` and `scoring.py` | `f1_config.py`, imports |
| Tie-break columns stored | `Driver Race Pts`, `Constructor Race Pts`, `Top Driver Score`, `Best Finish Pos` | `scoring.py:270-272, 326-331` |

---

## 2. Partially Implemented ⚠️

| Rule | Gap | Code Location |
|------|-----|---------------|
| Pit lane: “drivers below their original grid position move up” | FastF1 gives `GridPosition=0` for pit lane; original qualifying slot is not available. Drivers below *do* effectively move up because pit lane is excluded from on-grid, so positions 1–19 are assigned to the 19 on-grid drivers. But we cannot verify we match the exact intended ordering without qualifying data. | `build_fantasy_grid` |
| Grid penalty = actual starting place | Implemented only to the extent FastF1 reports actual grid. If a driver gets a 5-place penalty, FastF1’s `GridPosition` should already reflect that. No explicit penalty handling. | N/A – relies on FastF1 |
| Fastest lap only if driver finished | Implemented: we only add fastest lap inside the `_finished` branch. Rule does not explicitly require “must finish,” but current behavior is conservative. | `scoring.py:163-178` |

---

## 3. Still Missing ❌

| Item | Description |
|------|-------------|
| Sprint scoring | Not implemented; structure left ready for future addition. |
| Tie-break sorting | Data stored; no sorting by tie-break rules yet. |
| Explicit handling of “black flagged” for constructors | Driver black flag handled; constructor rule only mentions DSQ/excluded. |
| Fallback if `session.laps` is empty | `pick_fastest()` could fail; wrapped in try/except but laps fallback logic may be brittle. |

---

## 4. Risky Assumptions

1. **`GridPosition=0` means pit lane**  
   FastF1 uses 0 for pit lane; some feeds use 20. Code only checks `g == 0`. Other values not handled.

2. **DNS = 0 laps OR “Did not start” OR “Withdrawn”**  
   A driver who stalls on formation lap and is pushed away might have a different status. Edge cases not covered.

3. **`_finished` = “Finished” or status starting with “+”**  
   Assumes “+ 1 Lap”, “+ 2 Laps” etc. reflect classified finishers. Other statuses (e.g. “Retired”, “Accident”) correctly excluded.

4. **Fastest lap driver identity**  
   `session.laps.pick_fastest()['Driver']` returns 3-letter code (e.g. "VER"). Doc confirms this. If a DSQ driver set fastest lap, F1 removes it; FastF1 may still return that driver. We already exclude DSQ drivers from fastest lap points.

5. **Constructor `TeamName` matching**  
   Fuzzy match uses `str.contains`; could cause false positives if names overlap (e.g. “Williams” vs “Williams F1 Team” vs another team containing “Williams”).

6. **`ClassifiedPosition` for retirees**  
   DNF drivers can have `"R"`, `"N"`, etc. `safe_int(..., 999)` handles these; position gain is not awarded. Correct.

---

## 5. FastF1 vs League Rules – Data Mismatches

| Scenario | FastF1 Behavior | League Rule | Risk |
|----------|-----------------|-------------|------|
| Pit lane original grid | `GridPosition=0` only | Need qualifying slot for “drivers below move up” | Medium – current logic approximates via exclusion |
| Post-race penalties | `ClassifiedPosition` reflects final result | Use final classified order | Low – FastF1 typically correct |
| Deleted fastest lap | FastF1 may still report it | League may expect FIA-validated fastest lap | Low – would need cross-check |
| Red-flag race | Partial results; laps may be incomplete | Rule assumes full-race data | Medium – no special handling |
| Team name changes | e.g. “Alfa Romeo” → “Kick Sauber” | `CONSTRUCTOR_MAP` must be updated | Medium – manual upkeep |

---

## 6. Five Concrete Race Scenarios

### Scenario 1: Normal race, no incidents

**Setup:** VER P1, HAM P2, LEC P3. All finish. VER fastest lap.

**Flow:**
- `build_fantasy_grid`: 20 drivers on grid, no DNS, no pit lane → positions 1–20 as given.
- VER: grid 20, laps 78, finish 1 → 20 + 78 + 20 + 25 + 25 = 168.
- HAM: grid 19, laps 78, finish 2 → 19 + 78 + 18 + 18 = 133.
- LEC: grid 18, laps 78, finish 3 → 18 + 78 + 16 + 15 = 127.

**Verification:** Correct.

---

### Scenario 2: Pit lane start

**Setup:** 20 cars. PER qualified P5, starts from pit lane (`GridPosition=0`). Others P1–4, P6–20 on grid.

**Flow:**
- `build_fantasy_grid`: PER in `pit_lane_drivers`, 19 others in `on_grid` with grids 1–4, 6–20.
- Sorted on-grid: 1,2,3,4,6,7,…,20 → fantasy 1–19.
- PER fantasy position = 20.
- PER gets grid pts: 21 − 20 = 1 ✓
- Driver in old P6 gets fantasy P5 and grid pts: 21 − 5 = 16 ✓ (moved up)

**Verification:** Correct.

---

### Scenario 3: Formation lap non-starter

**Setup:** BOT qualified P8, retires on formation lap. Laps=0, Status e.g. “Did not start” or “Withdrawn” or “Accident”.

**Flow:**
- `_did_not_start("...", 0)` → True.
- BOT in `dns_abbrs`.
- `score_driver`: `abbr in dns_abbrs` → return 0, 0, None.
- BOT scores 0 for the weekend ✓
- On-grid: 19 drivers with grids 1–7, 9–20. Fantasy 1–19. Old P9 gets fantasy P8 ✓

**Verification:** Correct.

**Edge:** If status is e.g. “Accident” with 0 laps, we treat as DNS. If status is “Accident” with 1 lap (crossed line then crashed), we would not treat as DNS. Correct.

---

### Scenario 4: Driver disqualified after race

**Setup:** NOR finished P2, then DSQ. Status = “Disqualified”.

**Flow:**
- NOR not DNS, in fantasy grid.
- Grid points: added.
- `_disqualified(status)` → True.
- Apply −20 and return early.
- No laps, no finish, no fastest lap ✓

**Verification:** Correct.

**Edge:** If DSQ driver set fastest lap, we never add fastest-lap points because we return before that line. Correct.

---

### Scenario 5: Constructor – one finisher, one retirement

**Setup:** Ferrari: LEC P3 (finishes), SAI retires lap 10 (Status “Gearbox” or similar).

**Flow:**
- `_finished(SAI)` → False → SAI not in `finishers`.
- `finishers` = [LEC].
- DSQ cars: 0.
- `pts = 0 − 0 + 1*10 + 15 = 25` ✓ (10 for one finisher + 15 for P3)

**Verification:** Correct.

---

## 7. Potential Bugs

1. **`pick_fastest()` on empty/short races**  
   Wrapped in try/except; no fastest lap awarded if it fails. Acceptable.

2. **`session.laps.pick_driver(abbr)` for lap count**  
   `pick_driver` deprecated; may break in future FastF1 versions. Should migrate to `pick_drivers()`.

3. **Constructor fuzzy match**  
   `str.contains(official_team)` – e.g. “Alpine” matches “Alpine F1 Team” but could match unintended strings. Low risk with current team names.

4. **Best Finish Pos = 999**  
   Stored when no driver finishes. Tie-break logic must treat 999 as “no finish”.

---

## 8. Summary

- Core rules (grid, laps, position gain, finish, DSQ, constructor scoring, DNS, pit lane) are implemented correctly.
- Pit lane “original grid” handling is approximated via FastF1 data; full fidelity would need qualifying data.
- Fastest lap comparison uses 3-letter abbreviation; FastF1 Laps `Driver` column matches.
- Risk areas: edge DNS/status values, red-flag races, and constructor name matching.
