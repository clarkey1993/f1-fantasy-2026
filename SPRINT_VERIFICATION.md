# Sprint Implementation Verification Report

## 1. Does a Sprint event use FastF1 session type 'S'?

**Verified YES.** `scoring.py:257-259`:

```python
if session_type is None:
    session_type = SESSION_SPRINT if is_sprint_event(round_name) else SESSION_RACE
...
session = fastf1.get_session(year, event_for_lookup, session_type)
```

When `is_sprint_event(round_name)` is True (e.g. "China Sprint"), `session_type` is `SESSION_SPRINT` which is `'S'` (line 15).

---

## 2. Does a Grand Prix use FastF1 session type 'R'?

**Verified YES.** Same logic: when the race name does not contain "sprint", `session_type` is `SESSION_RACE` (`'R'`).

---

## 3. Does selecting "China Sprint" correctly load the China event and Sprint session?

**Verified YES.**

- `is_sprint_event("China Sprint")` → True (`scoring.py:26` — `'sprint' in "china sprint"`)
- `normalize_event_name("China Sprint")` → `"China"` (`scoring.py:30-34` — strips `" Sprint"` suffix)
- `fastf1.get_session(year, "China", 'S')` → loads Chinese GP event, Sprint session (`scoring.py:259`)

FastF1 accepts "China" for the Chinese Grand Prix and `'S'` for the Sprint session.

---

## 4. Does Sprint scoring use the exact same scoring logic as the GP?

**Verified YES.** Sprint and GP share the same path:

- Both use `session.results` → `build_fantasy_grid` → `score_driver` / `score_constructor`
- No branching on `session_type`; scoring is driven only by `results` and `session`
- Same logic for: grid points, laps, position gain, finishing points, fastest lap, constructor points, DSQ deductions

---

## 5. Does Sprint sync add another £5 to Total Spent?

**Verified YES.** `scoring.py:361`:

```python
df['Total Spent'] += 5.0
```

This runs for every sync (Sprint or GP). Each Sprint and each GP sync adds £5.

---

## 6. Does Sprint sync apply payouts exactly like a normal race?

**Verified YES.** `scoring.py:354-363`:

```python
if race_payouts:
    df['Weekend_Rank'] = df['Last Race Pts'].rank(ascending=False, method='min').astype(int)
    for i, amt in enumerate(race_payouts):
        target = i + 1
        mask = df['Weekend_Rank'] == target
        if mask.any():
            df.loc[mask, 'Total Winnings'] += float(amt)
```

- Rank is by `Last Race Pts` (Sprint or GP points)
- Same payout array from admin (p1, p2, p3, p_rest×12 = top 15)
- Payouts added to `Total Winnings` the same way for both event types

---

## 7. Does anything in the leaderboard or latest results view break?

**Verified NO.** Both views work correctly with Sprint as a separate scored event.

### Leaderboard (home)

- **Overall Standings:** Uses `Current Score` and `Total Winnings`, which accumulate across Sprints and GPs. Correct.
- **Latest Race Results:** Uses `Last Race Pts` sorted descending, with `DisplayPos` as `(Previous Pos) Weekend Rank`. Shows the most recently synced event (Sprint or GP). Correct.

### Data flow

- `Last Race Pts` = points from the last sync (Sprint or GP)
- `Current Score` = running total of all event points
- `Previous Pos` = overall rank before the last sync
- `race_results` is built by sorting on `Last Race Pts`; no dependency on event type

### Semantic note

- Card title is "Latest Race Results". When the last sync was a Sprint, it shows Sprint points but the word "Race" is technically inaccurate. Display and data are still correct. Optional improvement: rename to "Latest Event Results" if desired.

---

## Remaining Edge Cases

| Edge case | Status | Notes |
|-----------|--------|-------|
| `"China  Sprint"` (extra space) | `normalize` would not strip | `" China  Sprint".strip().lower().endswith(' sprint')` is False; would pass `"China  Sprint"` to FastF1; fuzzy match may still work |
| `"Sprint"` alone | Treated as Sprint | `is_sprint_event("Sprint")` = True; not in admin list |
| Non-sprint event named with "sprint" | Misclassified | e.g. "Sprint Shootout" in a future list would trigger Sprint logic; not currently used |
| Sync order (Sprint before GP) | Correct behaviour | Commissioner must sync in weekend order for historical accuracy; app does not enforce |
| Test mode | Uses Race only | `scoring.py:251` always uses `SESSION_RACE`; Sprint is never used in test mode |

---

## Summary

All seven checks pass. Sprint and GP are treated as separate events with the same scoring rules, £5 each, and independent payouts. Leaderboard and latest results views behave correctly. No breaking changes identified.
