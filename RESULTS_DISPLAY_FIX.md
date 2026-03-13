# Latest Results Display Fix – Root Cause & Summary

## Root Cause

Sprint Qualifying (and some other qualifying-style sessions) showed all rows as DNF because:

1. **Position source mismatch**  
   The code used `Position` and `ClassifiedPosition`. For Sprint Qualifying, FastF1 can leave `Position` as NaN and use different fields. The logic then fell through to `ClassifiedPosition`, and when that was also NaN or an unexpected value, the result was treated as invalid and turned into DNF.

2. **Over-aggressive DNF mapping**  
   Any non-numeric value (including `nan` when both columns were empty) was converted to DNF. Qualifying sessions often have NaN in these columns, so all drivers were shown as DNF.

3. **Session type detection**  
   Detection relied on `'Qualifying' in session.name`, which works for “Sprint Qualifying”, but:
   - Timing columns can be `SQ1`, `SQ2`, `SQ3` instead of `Q1`, `Q2`, `Q3`.
   - Session type should be inferred from the available columns as well, not only from the name.

4. **No fallback for position**  
   For qualifying, results are sorted by finishing position. When explicit position fields are missing, using the row index (1-based) as the position is a valid fallback.

## Fix Summary

- Added `_session_display_type()` to classify sessions (qualifying vs race vs practice) from both `session.name` and the available columns.
- Added `_resolve_position()` to use several sources for position (Position, ClassifiedPosition, GridPosition, then row index for qualifying) and only treat explicit non-position values (R, D, E, W, F, N, etc.) as DNF.
- Added `_qualifying_time_cols()` to support both `Q1/Q2/Q3` and `SQ1/SQ2/SQ3`.
- Added `_format_timedelta()` for consistent time display.

## Impact on Sprint Scoring

**Scoring logic is unchanged.**  
`get_latest_results_data()` is only used for the Latest News & Results page. Sprint scoring in `scoring.py` uses `fastf1.get_session(..., 'S')` and its own handling of `session.results`, and does not call `get_latest_results_data()`.
