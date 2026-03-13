"""
F1 Fantasy race scoring engine.
Uses shared f1_config for driver/constructor mappings.
"""
import fastf1
import pandas as pd
import os
import ast
import random
import re
import logging

from f1_config import DRIVER_MAP, CONSTRUCTOR_MAP, app_constructor_to_fastf1

# Session types: 'R' = Race, 'S' = Sprint
SESSION_RACE = 'R'
SESSION_SPRINT = 'S'

# Standard F1 finishing points (P1-P10)
FINISH_POINTS = {1: 25, 2: 18, 3: 15, 4: 12, 5: 10, 6: 8, 7: 6, 8: 4, 9: 2, 10: 1}

# Tie-break column names (stored in dataframe for leaderboard sorting)
TIEBREAK_COLS = ['Driver Race Pts', 'Constructor Race Pts', 'Top Driver Score', 'Best Finish Pos', 'Prior Best Finish Pos']

# Leaderboard sort: official tie-break order. Best Finish Pos / Prior Best Finish Pos: ascending (lower=better)
LEADERBOARD_SORT_BY = [
    'Current Score', 'Total Winnings',
    'Driver Race Pts',      # 1. driver pts weekend
    'Top Driver Score',     # 2-3. race pts / highest driver (approx)
    'Constructor Race Pts', # 4. constructor pts weekend
    'Best Finish Pos',      # 5. highest placed driver (lower=better)
    'Prior Best Finish Pos',# 6. prior race best finish (lower=better)
    'Name',
]
LEADERBOARD_SORT_ASCENDING = [False, False, False, False, False, True, True, True]


def _clean_race_name(race_name):
    """Trim leading/trailing spaces and collapse repeated internal spaces to a single space."""
    if race_name is None or (isinstance(race_name, str) and not race_name):
        return ""
    s = str(race_name).strip()
    return " ".join(s.split())


def is_sprint_event(race_name):
    """True if the admin-selected race name indicates a Sprint. Only matches when the cleaned name ends with 'Sprint' (e.g. 'China Sprint', 'China  Sprint')."""
    cleaned = _clean_race_name(race_name)
    return cleaned and cleaned.lower().endswith("sprint")


def normalize_event_name(race_name):
    """Returns the FastF1 event name: cleaned, with 'Sprint' suffix removed if present. E.g. 'China Sprint' -> 'China'."""
    cleaned = _clean_race_name(race_name)
    if not cleaned:
        return ""
    if cleaned.lower().endswith("sprint"):
        base = cleaned[: -len("sprint")].rstrip()
        return base
    return cleaned


# Sprint/GP matching logic summary:
# 1. _clean_race_name: trim leading/trailing spaces, collapse internal whitespace to single space.
# 2. is_sprint_event: True only if cleaned name ends with "sprint" (case-insensitive).
# 3. normalize_event_name: clean, then strip trailing "Sprint" (case-insensitive) if present; else return cleaned name.
# Examples: "China Sprint" / "China  Sprint" / " China Sprint " -> Sprint, event "China". "China" -> GP, event "China".


def safe_int(val, default=0):
    """Safely converts a value to int."""
    try:
        if pd.isna(val) or str(val).strip() == '':
            return default
        return int(float(val))
    except (ValueError, TypeError):
        return default


def _finished(status):
    """
    True if driver crossed the finish line (classified finisher).
    Accepts: 'Finished', '+1 Lap', '+2 Laps', '+X Lap(s)', 'Finished (+1 Lap)', etc.
    Excludes: DNFs, retirements, disqualified, excluded (handled elsewhere).
    """
    if status is None or (isinstance(status, float) and pd.isna(status)):
        return False
    s = str(status).strip().lower()
    if not s:
        return False
    # Explicit exclusions (DNF/DSQ - do not treat as finisher)
    if any(x in s for x in ('disqualified', 'excluded', 'black flag', 'retired', 'accident', 'crash', 'collision', 'engine', 'gearbox', 'spun off', 'suspension', 'brakes', 'electrical', 'hydraulics', 'did not start', 'withdrawn')):
        return False
    # Finished (exact or with suffix like "Finished (+1 Lap)")
    if 'finished' in s:
        return True
    # +X Lap / +X Laps / + X Lap(s) - any laps behind format
    if re.search(r'\+\s*\d+\s*laps?', s):
        return True
    # Legacy: status starts with + (catches other variations)
    if s.startswith('+'):
        return True
    return False


def _did_not_start(status, laps):
    """True if driver never passed the race start line (e.g. formation lap retirement)."""
    s = str(status).lower()
    if 'did not start' in s or 'withdrawn' in s:
        return True
    if laps == 0:
        return True
    return False


def _pit_lane_start(grid_pos):
    """True if driver started from pit lane (GridPosition typically 0 or 20 in some feeds)."""
    if grid_pos is None or pd.isna(grid_pos):
        return False
    g = safe_int(grid_pos, -1)
    return g == 0


def _disqualified(status):
    """True if driver was disqualified, excluded, or black flagged."""
    s = str(status).lower()
    return 'disqualified' in s or 'excluded' in s or 'black flag' in s


def _parse_picks(row):
    """Parse Picks string into list. Returns empty list on error."""
    try:
        raw = str(row['Picks']).replace('"', '"').replace('"', '"').replace("'", "'").replace("'", "'")
        return ast.literal_eval(raw)
    except (ValueError, SyntaxError):
        return []


def build_fantasy_grid(results):
    """
    Build fantasy-adjusted starting grid from race results.
    Handles: pit lane starters (get pos 20, others move up), DNS (score 0, others move up).
    Returns: dict abbr -> fantasy_grid_position (1-20), and set of DNS abbrs.
    """
    # Build list of (abbr, original_grid, is_pit_lane, is_dns)
    rows = []
    for _, r in results.iterrows():
        abbr = r.get('Abbreviation')
        if not abbr:
            continue
        grid = safe_int(r.get('GridPosition'), 0)
        laps = safe_int(r.get('Laps'), 0)
        status = str(r.get('Status', ''))
        is_dns = _did_not_start(status, laps)
        is_pit = _pit_lane_start(r.get('GridPosition')) and not is_dns
        rows.append((abbr, grid, is_pit, is_dns))

    # Sort by original grid (pit lane = 0 will sort first; we treat 0 as "behind" grid)
    rows.sort(key=lambda x: (x[2], x[1]))  # pit lane first (is_pit True=1), then by grid
    # Actually: we need grid order. Pit lane has grid 0. So sort by grid - 0 will be last or first.
    # Official grid: 1,2,3,...,20. Pit lane might be 0 or 20. Let's sort by grid ascending;
    # 0 comes first, then 1,2,... So we want: non-pit-lane by grid, then pit lane at end.
    rows.sort(key=lambda x: (999 if x[2] else x[1], x[1]))  # pit lane at end, else by grid

    # Separate DNS from the rest
    dns_abbrs = {abbr for abbr, _, _, is_dns in rows if is_dns}
    active = [(abbr, grid, is_pit) for abbr, grid, is_pit, is_dns in rows if not is_dns]

    # Build ordered list of drivers in fantasy grid positions
    # Remove pit lane from their slot, append at end. Renumber 1..N.
    on_grid = []
    pit_lane_drivers = []
    for abbr, grid, is_pit in active:
        if is_pit:
            pit_lane_drivers.append(abbr)
        else:
            on_grid.append((abbr, grid))

    # Sort on_grid by original grid position
    on_grid.sort(key=lambda x: x[1])
    # Positions 1 to len(on_grid) for on-grid drivers
    fantasy = {}
    for i, (abbr, _) in enumerate(on_grid):
        fantasy[abbr] = i + 1
    # Pit lane drivers get positions at the end
    for j, abbr in enumerate(pit_lane_drivers):
        fantasy[abbr] = len(on_grid) + j + 1

    return fantasy, dns_abbrs


def score_driver(d, fantasy_grid, dns_abbrs, fastest_lap_abbr, max_laps, session, abbr):
    """
    Score a single driver. Returns (points, race_only_points, classified_position or None).
    """
    if abbr in dns_abbrs:
        return 0, 0, None

    status = str(d.get('Status', ''))
    laps = safe_int(d.get('Laps'), 0)
    if laps == 0:
        try:
            dlaps = session.laps.pick_driver(abbr)
            if len(dlaps) > 0:
                laps = len(dlaps)
        except Exception:
            pass
    if laps == 0 and _finished(status):
        laps = int(max_laps)

    grid_pos = fantasy_grid.get(abbr)
    if grid_pos is None:
        grid_pos = 20

    pts = 0
    race_pts = 0

    # Grid points: 20 for P1 down to 1 for P20
    grid_pts = max(0, 21 - grid_pos)
    pts += grid_pts
    race_pts += grid_pts

    if _disqualified(status):
        pts -= 20
        race_pts -= 20
        return pts, race_pts, None

    # Laps
    pts += laps
    race_pts += laps

    if not _finished(status):
        return pts, race_pts, None

    finish = safe_int(d.get('ClassifiedPosition'), 999)
    # Position gain: only if positive
    gain = grid_pos - finish
    if gain > 0:
        pts += gain
        race_pts += gain

    pts += FINISH_POINTS.get(finish, 0)
    race_pts += FINISH_POINTS.get(finish, 0)

    if abbr == fastest_lap_abbr:
        pts += 25
        race_pts += 25

    return pts, race_pts, finish


def score_constructor(pick, results, session):
    """
    Score a single constructor. Returns (points,).
    10 per finishing car, best car's finish points, -10 per DSQ car.
    """
    official_team = app_constructor_to_fastf1(pick)
    t_data = results[results['TeamName'] == official_team]
    match_method = "exact"
    if t_data.empty:
        # Fallback: fuzzy match (e.g. "Kick Sauber" in config vs "Kick Sauber F1 Team" in results)
        t_data = results[results['TeamName'].str.contains(official_team, case=False, na=False)]
        match_method = "contains"

    abbrs = t_data['Abbreviation'].tolist() if not t_data.empty and 'Abbreviation' in t_data.columns else []
    logging.debug("[scoring] Constructor pick=%s -> FastF1=%s | rows=%d | match=%s | drivers=%s",
                  pick, official_team, len(t_data), match_method, abbrs)

    if t_data.empty:
        logging.warning("[scoring] Constructor %s (%s): 0 rows matched in results", pick, official_team)
        return 0

    pts = 0

    dq_cars = t_data[t_data['Status'].str.contains('Disqualified|Excluded', na=False, case=False)]
    pts -= len(dq_cars) * 10

    finishers = []
    for _, car in t_data.iterrows():
        if _finished(car['Status']):
            finishers.append(car)

    # Debug safeguard: team in results but no finishers detected
    if len(finishers) == 0 and len(t_data) > 0:
        statuses = [str(c.get('Status', '')) for _, c in t_data.iterrows()]
        logging.warning("[scoring] Constructor %s (%s): 0 finishers but %d car(s) in results. Statuses: %s",
                       pick, official_team, len(t_data), statuses)

    pts += len(finishers) * 10

    if finishers:
        best_pos = min(safe_int(c.get('ClassifiedPosition'), 999) for c in finishers)
        pts += FINISH_POINTS.get(best_pos, 0)

    return pts


def calculate_race_scores(df, year, round_name, race_payouts=None, is_test=False, session_type=None):
    """
    Calculates scores for a given race or sprint and updates the DataFrame.
    Uses the same scoring rules for both. Sprint and Grand Prix are separate £5 events.
    Args:
        is_test: False = production sync. True = random Grand Prix from last season.
                 'sprint' = random Sprint from last season (if available).
        session_type: 'R' for Race, 'S' for Sprint. Auto-derived from round_name if None.
    Returns: (updated_df, log_message)
    """
    try:
        if not os.path.exists('f1_cache'):
            os.makedirs('f1_cache')
        fastf1.Cache.enable_cache('f1_cache')

        event_label = round_name  # For success message

        if is_test:
            test_year = year - 1
            schedule = fastf1.get_event_schedule(test_year, include_testing=False)
            if is_test == 'sprint':
                # Find events that have a Sprint session
                sprint_formats = ('sprint', 'sprint_shootout', 'sprint_qualifying')
                if 'EventFormat' not in schedule.columns:
                    return df, f"No Sprint events found for {test_year} (schedule format unknown)."
                sprint_mask = schedule['EventFormat'].isin(sprint_formats)
                sprint_rounds = schedule.loc[sprint_mask, 'RoundNumber'].dropna().unique().tolist()
                if not sprint_rounds:
                    return df, f"No Sprint events found for {test_year}."
                rnd = random.choice(sprint_rounds)
                session = fastf1.get_session(test_year, int(rnd), SESSION_SPRINT)
                session.load(telemetry=False, weather=False)
                event_label = f"TEST: {session.event['EventName']} Sprint {test_year}"
            else:
                # Grand Prix stress test
                rounds_list = schedule['RoundNumber'].unique().tolist()
                rnd = random.choice(rounds_list) if rounds_list else 1
                session = fastf1.get_session(test_year, rnd, SESSION_RACE)
                session.load(telemetry=False, weather=False)
                event_label = f"TEST: {session.event['EventName']} Grand Prix {test_year}"
        else:
            if session_type is None:
                session_type = SESSION_SPRINT if is_sprint_event(round_name) else SESSION_RACE
            event_for_lookup = normalize_event_name(round_name)
            session = fastf1.get_session(year, event_for_lookup, session_type)
            session.load(telemetry=False, weather=False)
            event_label = f"{round_name} ({'Sprint' if session_type == SESSION_SPRINT else 'Grand Prix'})"

        results = session.results
        if results.empty:
            return df, f"No results available for {event_label}."

        # Log scoring run identity (mode, year, event, session)
        mode = "sprint test" if is_test == "sprint" else ("test" if is_test else "production")
        actual_year = (year - 1) if is_test else year
        year_label = "league_year" if not is_test else "test_year(prev_season)"
        event_for_log = normalize_event_name(round_name)
        ff1_event_name = str(session.event.get("EventName", "?")) if hasattr(session, "event") and session.event is not None else "?"
        sess_type = "Sprint" if (is_test == "sprint" or (not is_test and session_type == SESSION_SPRINT)) else "Grand Prix"
        logging.warning(
            "[scoring] RUN IDENTITY | mode=%s | %s=%s | event=%s | normalized=%s | session_type=%s | FastF1_loaded=%s %s",
            mode, year_label, actual_year, round_name, event_for_log, sess_type, ff1_event_name, actual_year
        )

        max_laps = 0
        try:
            max_laps = results['Laps'].max()
            if pd.isna(max_laps) or max_laps == 0:
                max_laps = session.laps['LapNumber'].max() if len(session.laps) > 0 else 0
        except Exception:
            pass
        max_laps = int(max_laps) if max_laps else 0

        fastest_lap_abbr = None
        try:
            fastest_lap_abbr = session.laps.pick_fastest()['Driver']
        except Exception:
            pass

        fantasy_grid, dns_abbrs = build_fantasy_grid(results)

        # Debug: log actual FastF1 TeamNames (once per scoring run)
        if 'TeamName' in results.columns:
            unique_teams = sorted(results['TeamName'].dropna().unique().tolist())
            logging.info("[scoring] FastF1 TeamNames in results: %s", unique_teams)

        if df.empty:
            return df, "No players found in the league data."

        for c in ['Current Score', 'Total Winnings', 'Previous Pos', 'Last Race Pts', 'Total Spent']:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
            else:
                df[c] = 0

        df['Previous Pos'] = df['Current Score'].rank(ascending=False, method='min').fillna(0).astype(int)

        for col in TIEBREAK_COLS:
            if col not in df.columns:
                df[col] = 999 if 'Best Finish' in col or 'Prior' in col else 0
            if col in ('Best Finish Pos', 'Prior Best Finish Pos'):
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(999)

        df['Previous Pos'] = df['Current Score'].rank(ascending=False, method='min').fillna(0).astype(int)

        race_totals = []
        driver_race_pts_list = []
        constructor_race_pts_list = []
        top_driver_scores = []
        best_finish_positions = []

        for _, row in df.iterrows():
            picks = _parse_picks(row)
            if not picks:
                race_totals.append(0)
                driver_race_pts_list.append(0)
                constructor_race_pts_list.append(0)
                top_driver_scores.append(0)
                best_finish_positions.append(999)
                continue

            drivers = picks[:10]
            constructors = picks[10:]

            total = 0
            driver_race_total = 0
            constructor_race_total = 0
            top_driver = 0
            best_finish = 999

            for pick in drivers:
                if pick not in DRIVER_MAP:
                    continue
                abbr = DRIVER_MAP[pick]
                d_data = results[results['Abbreviation'] == abbr]
                if d_data.empty:
                    continue
                d = d_data.iloc[0]
                pts, race_pts, finish_pos = score_driver(
                    d, fantasy_grid, dns_abbrs, fastest_lap_abbr, max_laps, session, abbr
                )
                total += pts
                driver_race_total += race_pts
                if race_pts > top_driver:
                    top_driver = race_pts
                if finish_pos is not None and finish_pos < best_finish:
                    best_finish = finish_pos

            for pick in constructors:
                c_pts = score_constructor(pick, results, session)
                total += c_pts
                constructor_race_total += c_pts

            race_totals.append(total)
            driver_race_pts_list.append(driver_race_total)
            constructor_race_pts_list.append(constructor_race_total)
            top_driver_scores.append(top_driver)
            best_finish_positions.append(best_finish if best_finish < 999 else 999)

        df['Last Race Pts'] = race_totals
        df['Driver Race Pts'] = driver_race_pts_list
        df['Constructor Race Pts'] = constructor_race_pts_list
        df['Top Driver Score'] = top_driver_scores
        df['Prior Best Finish Pos'] = df['Best Finish Pos']  # Save before overwrite for tie-break 6
        df['Best Finish Pos'] = best_finish_positions

        df['Current Score'] = df['Current Score'] + df['Last Race Pts']

        if race_payouts:
            df['Weekend_Rank'] = df['Last Race Pts'].rank(ascending=False, method='min').astype(int)
            for i, amt in enumerate(race_payouts):
                target = i + 1
                mask = df['Weekend_Rank'] == target
                if mask.any():
                    df.loc[mask, 'Total Winnings'] += float(amt)
            df = df.drop(columns=['Weekend_Rank'])

        df['Total Spent'] += 5.0
        sort_cols = [c for c in LEADERBOARD_SORT_BY if c in df.columns]
        sort_asc = [LEADERBOARD_SORT_ASCENDING[i] for i, c in enumerate(LEADERBOARD_SORT_BY) if c in df.columns]
        df = df.sort_values(by=sort_cols, ascending=sort_asc)
        df['Pos'] = df['Current Score'].rank(ascending=False, method='min').fillna(0).astype(int)

        return df, f"Successfully synced {event_label}!"

    except Exception as e:
        return df, f"Error during sync: {str(e)}"
