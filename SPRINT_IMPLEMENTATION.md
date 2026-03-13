# Sprint Race Implementation Summary

## How Sprint Weekends Now Work

A Sprint weekend (e.g. China, Miami, Austria) counts as **two separate race events** in the fantasy league:

1. **Sprint race** – Saturday sprint (admin selects "China Sprint", "Miami Sprint", etc.)
2. **Grand Prix** – Sunday race (admin selects "China", "Miami", etc.)

### Per-event behaviour (both Sprint and GP)

- £5/€5 entry cost each
- Top 15 payout (configurable in admin)
- Same scoring: grid points, laps, position gain, finishing points, fastest lap, constructor points, deductions
- Each updates the leaderboard independently (adds to Current Score, Last Race Pts, etc.)

### Admin workflow

1. After the Sprint: select "China Sprint" (or other sprint event) → Sync → £5 charged, payouts applied
2. After the GP: select "China" → Sync → £5 charged, payouts applied

No code or UI changes needed; selection from the existing race dropdown drives behaviour.

---

## Code Changes

### scoring.py

- `is_sprint_event(race_name)` – returns True if name contains "sprint"
- `normalize_event_name(race_name)` – strips " Sprint" suffix for FastF1 lookup
- `calculate_race_scores(..., session_type=None)` – new optional `session_type`; if None, derived from `race_name`
- Uses FastF1 session 'S' for Sprints, 'R' for Races
- Success messages state whether the synced event was a "Sprint" or "Grand Prix"

### app.py

- No changes – admin sync continues to pass `race_name`; scoring infers Sprint vs GP from the name

---

## Assumptions for Commissioner Confirmation

1. **Sprint and GP both £5** – Each event costs £5 and awards payouts separately.
2. **Same scoring for both** – Sprint uses the same rules (grid, laps, gain, finish, fastest lap, constructor, deductions).
3. **Race name format** – Admin list uses "China Sprint", "Miami Sprint", etc.; FastF1 event name is the base (e.g. "China").
4. **Test mode** – Stress test always uses a main Race session ('R'), not Sprint.
5. **Event ordering** – Commissioner must sync Sprint before GP for the same weekend when running historical data.
