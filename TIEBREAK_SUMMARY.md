# Tie-Break Implementation Summary

## Tie-Break Rules Now Fully Applied

| Rule | Implementation | Column(s) Used |
|------|----------------|----------------|
| 1. Points scored by drivers over the weekend | Applied | `Driver Race Pts` |
| 2. Points scored by drivers during the race including fastest lap | Same as 1 (stored per event) | `Driver Race Pts` |
| 3. Highest different top-scoring driver | **Approximated** | `Top Driver Score` |
| 4. Constructors points over the weekend | Applied | `Constructor Race Pts` |
| 5. Highest placed different driver | **Approximated** | `Best Finish Pos` |
| 6. Highest finishing position from prior race | Applied | `Prior Best Finish Pos` |

## Remaining Approximations

- **Rule 3:** "Highest different top-scoring driver" requires per-driver scores and pairwise comparison. We use `Top Driver Score` (best single driver) as an approximation. True "different" would exclude shared drivers when comparing two tied managers.
- **Rule 5:** "Highest placed different driver" requires per-driver finish positions and pairwise comparison. We use `Best Finish Pos` (best classified finish among their drivers) as an approximation.
- **Rules 1–2:** "Driver points over the weekend" vs "during the race" are identical when we store one event. For sprint weekends, "weekend" would be Sprint + GP combined; we only have the last synced event. Using `Driver Race Pts` (last event) for both.

## Exact Sort Order Logic

```python
LEADERBOARD_SORT_BY = [
    'Current Score',        # Primary
    'Total Winnings',       # Secondary (financial)
    'Driver Race Pts',      # Tie-break 1 & 2
    'Top Driver Score',     # Tie-break 3 (approx)
    'Constructor Race Pts', # Tie-break 4
    'Best Finish Pos',      # Tie-break 5 (approx) — ascending (lower=better)
    'Prior Best Finish Pos',# Tie-break 6 — ascending (lower=better)
    'Name',                 # Final determinism
]
LEADERBOARD_SORT_ASCENDING = [False, False, False, False, False, True, True, True]
```

## Where Applied

- **Main leaderboard** (home): Uses `LEADERBOARD_SORT_BY` for display order.
- **Latest Race Results** (home): Uses same tie-break columns after `Last Race Pts` for weekend ranking.
- **Scoring output**: DataFrame is sorted by `LEADERBOARD_SORT_BY` before saving; `Pos` = rank by `Current Score`.
- **Previous Pos**: Rank by `Current Score` before adding new race points (tie-breaks affect display order, not rank values when tied).

## New Column

- **Prior Best Finish Pos**: Set at each sync from the previous `Best Finish Pos` before it is overwritten. Used for tie-break 6. Default 999 (no classified finish).
