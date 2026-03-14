from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
import datetime
import pandas as pd
import ast
import requests
import feedparser
import os
import scoring
from scoring import (
    LEADERBOARD_SORT_BY,
    LEADERBOARD_SORT_ASCENDING,
    is_sprint_event,
    normalize_event_name,
    get_team_scoring_breakdown,
    parse_picks_from_string,
)
import fastf1
import re
import gspread
import json
import shutil

from f1_config import (
    DRIVER_TEAM_MAP,
    TEAM_CONFIG,
    get_team_config,
    LEAGUE_YEAR,
    app_constructor_to_fastf1,
)

app = Flask(__name__)
app.secret_key = "dev_key_f1_2026"  # Required for session and flash messages

# Inject 'year' into all templates automatically
@app.context_processor
def inject_globals():
    return {
        'year': LEAGUE_YEAR,
        'now': datetime.datetime.now()
    }

@app.after_request
def add_security_headers(response):
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response

# --- CONFIGURATION & DATA HELPERS ---

SHEET_ID = "150YSDU3o1SiEM1WHpPEK9pNPnGUu03qxR26H77RnApw"
SHEET_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"
DATA_FILE = 'league_data.csv'
TEST_DATA_FILE = 'league_test_data.csv'
NOTICE_FILE = 'notice.txt'
HISTORY_FILE = 'race_sync_history.json'
SEASON_HISTORY_FILE = 'season_results_history.json'

# 2026 Sprint weekend bases: GP cannot be synced before its Sprint
SPRINT_WEEKEND_BASES = ('China', 'Miami', 'Canada', 'Great Britain', 'Netherlands', 'Singapore')

def get_gspread_client():
    """Authenticates with Google Sheets using Env Var, Secret File, or Local File."""
    try:
        # 1. Render Secret File (Best Practice)
        if os.path.exists('/etc/secrets/service_account.json'):
            print("🔑 Using Render Secret File")
            return gspread.service_account(filename='/etc/secrets/service_account.json')
            
        # 2. Environment Variable (JSON String)
        if os.environ.get('GOOGLE_SHEETS_CREDS_JSON'):
            print("🔑 Using Env Var Credentials")
            creds_dict = json.loads(os.environ.get('GOOGLE_SHEETS_CREDS_JSON'))
            return gspread.service_account_from_dict(creds_dict)

        # 3. Local Files
        for f in ['service_account.json', 'service_account.json.json']:
            if os.path.exists(f):
                print(f"🔑 Using Local File: {f}")
                return gspread.service_account(filename=f)
                
    except Exception as e:
        print(f"⚠️ Auth Error: {e}")
    
    return None

def get_driver_image(name):
    """Returns official F1 image URL or None."""
    # Map names to 2024 F1.com slugs
    slugs = {
        "Max Verstappen": "verstappen", "Sergio Perez": "perez",
        "Lewis Hamilton": "hamilton", "George Russell": "russell",
        "Charles Leclerc": "leclerc", "Carlos Sainz": "sainz", "Carlos Sainz Jnr": "sainz",
        "Lando Norris": "norris", "Oscar Piastri": "piastri",
        "Fernando Alonso": "alonso", "Lance Stroll": "stroll",
        "Esteban Ocon": "ocon", "Pierre Gasly": "gasly",
        "Alex Albon": "albon", "Alexander Albon": "albon",
        "Valtteri Bottas": "bottas", "Guanyu Zhou": "zhou",
        "Kevin Magnussen": "magnussen", "Nico Hulkenberg": "hulkenberg",
        "Yuki Tsunoda": "tsunoda", "Daniel Ricciardo": "ricciardo",
        "Liam Lawson": "lawson", "Oliver Bearman": "bearman",
        "Franco Colapinto": "colapinto"
    }
    
    slug = slugs.get(name)
    if slug:
        return f"https://media.formula1.com/content/dam/fom-website/drivers/2024Drivers/{slug}.jpg.img.1920.medium.jpg"
    return None

def fetch_google_sheet_data():
    """Attempts to fetch data from Google Sheets via API or CSV Export."""
    df = pd.DataFrame()
    # 1. Try API (gspread) - Best for private sheets
    gc = get_gspread_client()
    if gc:
        try:
            sh = gc.open_by_key(SHEET_ID)
            ws = sh.sheet1
            data = ws.get_all_records()
            df = pd.DataFrame(data)
            print("Fetched data via gspread API")
        except Exception as e:
            print(f"gspread fetch failed: {e}")

    # 2. Fallback to CSV Export - Good for public/link-shared sheets
    if df.empty:
        try:
            df = pd.read_csv(SHEET_URL)
            print("Fetched data via CSV export URL")
        except Exception as e:
            print(f"CSV export fetch failed: {e}")
            
    return df

def get_league_data():
    """Fetches data from local CSV or falls back to Google Sheet export."""
    df = pd.DataFrame()
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
    else:
        df = fetch_google_sheet_data()
        if not df.empty:
            save_league_data(df) # Save to local for next time

    # Ensure numeric columns exist (incl. tie-break cols from scoring)
    cols = ['Current Score', 'Total Winnings', 'Previous Pos', 'Last Race Pts', 'Total Spent',
            'Driver Race Pts', 'Constructor Race Pts', 'Top Driver Score', 'Best Finish Pos', 'Prior Best Finish Pos']
    for c in cols:
        if c not in df.columns:
            df[c] = 999 if c in ('Best Finish Pos', 'Prior Best Finish Pos') else 0
        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(999 if c in ('Best Finish Pos', 'Prior Best Finish Pos') else 0)
    
    # Ensure string columns exist and are filled (Fix for missing names/nicks)
    for c in ['Name', 'Nickname', 'Email', 'Picks']:
        if c not in df.columns:
            df[c] = ""
        df[c] = df[c].fillna("Unknown")
        
    return df

def save_league_data(df):
    """Saves to local CSV and attempts to sync to Google Sheet.
    Returns:
        True: Sync successful.
        'skipped': Sync was skipped (no credentials).
        False: Sync failed with an error.
    """
    # 1. Save Local
    df.to_csv(DATA_FILE, index=False)
    
    # 2. Try Google Sheet Sync (Push)
    gc = get_gspread_client()
    if gc:
        try:
            sh = gc.open_by_key(SHEET_ID)
            ws = sh.sheet1
            # Convert to list of lists, handling NaNs and types for Sheets
            # We use fillna('') because Sheets doesn't like NaN
            data = [df.columns.values.tolist()] + df.fillna('').astype(str).values.tolist()
            
            # SAFE UPDATE STRATEGY:
            # 1. Update cells (overwrites existing data)
            ws.update(range_name='A1', values=data)
            
            # 2. Resize sheet to match new data length (trims old rows at the bottom)
            # This prevents "ghost" rows if the new dataset is smaller than the old one
            ws.resize(rows=len(data))
            
            print("Synced to Google Sheet")
            return True # Success
        except Exception as e:
            print(f"Google Sheet Sync Failed: {e}")
            return False # Failure
    else:
        print(f"⚠️ Skipping Google Sheet Sync: No credentials found. Data saved locally only.")
        return 'skipped' # Skipped

# --- TEST DATA HELPERS (admin testing only, never touches production) ---

def get_test_league_data():
    """Loads test league data from league_test_data.csv.
    If file does not exist, initializes from a copy of current production league data.
    NEVER reads/writes production CSV or Google Sheets."""
    if os.path.exists(TEST_DATA_FILE):
        df = pd.read_csv(TEST_DATA_FILE)
    else:
        df = get_league_data().copy()
        save_test_league_data(df)
    cols = ['Current Score', 'Total Winnings', 'Previous Pos', 'Last Race Pts', 'Total Spent',
            'Driver Race Pts', 'Constructor Race Pts', 'Top Driver Score', 'Best Finish Pos', 'Prior Best Finish Pos']
    for c in cols:
        if c not in df.columns:
            df[c] = 999 if c in ('Best Finish Pos', 'Prior Best Finish Pos') else 0
        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(999 if c in ('Best Finish Pos', 'Prior Best Finish Pos') else 0)
    for c in ['Name', 'Nickname', 'Email', 'Picks']:
        if c not in df.columns:
            df[c] = ""
        df[c] = df[c].fillna("Unknown")
    return df

def save_test_league_data(df):
    """Saves test data to league_test_data.csv only. NEVER syncs to Google Sheets."""
    df.to_csv(TEST_DATA_FILE, index=False)

def reset_test_league_data():
    """Resets test leaderboard by copying current production league data to league_test_data.csv."""
    df = get_league_data().copy()
    save_test_league_data(df)

# --- PRODUCTION SYNC HISTORY (for duplicate & Sprint-before-GP validation) ---

def load_sync_history():
    """Load production sync history from race_sync_history.json. Returns list of dicts."""
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, 'r') as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []

def save_sync_history(history):
    """Save production sync history to race_sync_history.json."""
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2)

def add_sync_to_history(event_name, session_type):
    """Append a production sync to history."""
    history = load_sync_history()
    normalized = normalize_event_name(event_name)
    entry = {
        "event_name": event_name,
        "normalized": normalized,
        "session_type": "Sprint" if session_type == "Sprint" else "GP",
        "timestamp": datetime.datetime.now().isoformat()
    }
    history.append(entry)
    save_sync_history(history)

def update_sync_in_history(event_name, session_type):
    """Update existing history entry timestamp (for force resync). No duplicate entries."""
    history = load_sync_history()
    event_clean = (event_name or "").strip()
    now = datetime.datetime.now().isoformat()
    for e in history:
        if (e.get("event_name") or "").strip() == event_clean:
            e["timestamp"] = now
            e["session_type"] = "Sprint" if session_type == "Sprint" else "GP"
            save_sync_history(history)
            return
    # Edge case: not in history yet, add it (e.g. history was cleared)
    add_sync_to_history(event_name, session_type)

def is_event_already_synced(event_name):
    """True if this exact event has already been synced to production."""
    history = load_sync_history()
    for e in history:
        if (e.get("event_name") or "").strip() == (event_name or "").strip():
            return True
    return False

def is_gp_on_sprint_weekend(race_name):
    """True if selecting a GP on a weekend that has a Sprint (must sync Sprint first)."""
    if is_sprint_event(race_name):
        return False  # We're syncing Sprint, no check needed
    base = normalize_event_name(race_name)
    return base in SPRINT_WEEKEND_BASES

def sprint_already_synced_for_gp(gp_race_name):
    """For a GP like 'China', True if 'China Sprint' has been synced."""
    base = normalize_event_name(gp_race_name)
    sprint_name = f"{base} Sprint"
    return is_event_already_synced(sprint_name)

def get_recent_synced_events(limit=10):
    """Return the most recently synced production events for display."""
    history = load_sync_history()
    return list(reversed(history[-limit:])) if history else []


# --- SEASON RESULTS HISTORY (event-by-event tables, production-only) ---

def load_season_results_history():
    """Load season event results history from season_results_history.json. Returns list of dicts."""
    if not os.path.exists(SEASON_HISTORY_FILE):
        return []
    try:
        with open(SEASON_HISTORY_FILE, 'r') as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def rebuild_season_history_from_sync_history():
    """
    Rebuild season_results_history.json from race_sync_history.json.
    Replays production events on a COPY of league data; never modifies production.
    Returns True if rebuilt, False if recovery not possible.
    """
    sync_history = load_sync_history()
    if not sync_history:
        if not os.path.exists(HISTORY_FILE):
            print("[season-history] Cannot recover: race_sync_history.json missing. Season history unavailable.")
        else:
            print("[season-history] Cannot recover: race_sync_history.json is empty.")
        return False

    df = get_league_data()
    if df.empty:
        print("[season-history] Cannot recover: no league data.")
        return False

    df = df.copy()
    default_payouts = [20, 15, 10] + [5] * 12

    for c in ['Current Score', 'Total Winnings', 'Previous Pos', 'Last Race Pts', 'Total Spent',
              'Driver Race Pts', 'Constructor Race Pts', 'Top Driver Score']:
        if c in df.columns:
            df[c] = 0
    for c in ['Best Finish Pos', 'Prior Best Finish Pos']:
        if c in df.columns:
            df[c] = 999

    new_season_history = []
    for entry in sync_history:
        evt = (entry.get("event_name") or "").strip()
        if not evt:
            continue
        sess_type = entry.get("session_type", "GP")
        df, msg = scoring.calculate_race_scores(df, LEAGUE_YEAR, evt, default_payouts)
        if "Successfully" not in msg:
            print(f"[season-history] Rebuild failed at event '{evt}': {msg}")
            return False
        append_event_snapshot_to_history(new_season_history, evt, sess_type, df)

    save_season_results_history(new_season_history)
    print(f"[season-history] Recovered {len(new_season_history)} events from race_sync_history.json")
    return True


def _ensure_season_history_available():
    """If season history is empty but sync history exists, rebuild. No-op if history already present."""
    if load_season_results_history():
        return
    rebuild_season_history_from_sync_history()

def save_season_results_history(history):
    """Save season event results history to season_results_history.json."""
    with open(SEASON_HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2)

def _build_event_snapshot(event_name, session_type, df):
    """Build one event snapshot from df (which has Last Race Pts = points for this event)."""
    _race_sort_spec = [
        ('Last Race Pts', False), ('Driver Race Pts', False), ('Top Driver Score', False),
        ('Constructor Race Pts', False), ('Best Finish Pos', True), ('Prior Best Finish Pos', True), ('Name', True),
    ]
    race_sort_cols = [c for c, _ in _race_sort_spec if c in df.columns]
    race_sort_asc = [asc for c, asc in _race_sort_spec if c in df.columns]
    sorted_df = df.sort_values(by=race_sort_cols, ascending=race_sort_asc)
    results = []
    for i, (_, row) in enumerate(sorted_df.iterrows()):
        prev = int(row['Previous Pos']) if row.get('Previous Pos', 0) > 0 else None
        results.append({
            "pos": i + 1,
            "display_pos": f"({prev}) {i + 1}" if prev else str(i + 1),
            "name": str(row.get('Name', '')),
            "nickname": str(row.get('Nickname', '')),
            "event_pts": int(row.get('Last Race Pts', 0)),
            "total_winnings": float(row.get('Total Winnings', 0)),
        })
    return {
        "event_name": event_name,
        "normalized": normalize_event_name(event_name),
        "session_type": "Sprint" if session_type == "Sprint" else "GP",
        "timestamp": datetime.datetime.now().isoformat(),
        "results": results,
    }

def add_event_to_season_history(event_name, session_type, df):
    """Append one event snapshot to season results history. Production sync only."""
    entry = _build_event_snapshot(event_name, session_type, df)
    history = load_season_results_history()
    history.append(entry)
    save_season_results_history(history)

def append_event_snapshot_to_history(history_list, event_name, session_type, df):
    """Append one event snapshot to a history list. Used when rebuilding during force_sync."""
    history_list.append(_build_event_snapshot(event_name, session_type, df))

def _format_history_entry(entry):
    """Convert raw history entry to display dict with title, results, etc."""
    evt = entry.get("event_name", "")
    sess = entry.get("session_type", "GP")
    base = normalize_event_name(evt)
    if sess == "Sprint":
        title = f"{base} Sprint Results"
    else:
        title = f"{base} Grand Prix Results"
    return {
        "title": title,
        "event_name": evt,
        "session_type": sess,
        "normalized": base,
        "timestamp": entry.get("timestamp", ""),
        "results": entry.get("results", []),
    }

def get_current_weekend_events():
    """
    Return 0, 1, or 2 event display dicts for the homepage (current weekend only).
    - Normal GP weekend: one GP result table
    - Sprint weekend (both synced): Sprint first, GP second
    - Only one event synced: that one
    """
    _ensure_season_history_available()
    raw = load_season_results_history()
    if not raw:
        return []
    newest_first = list(reversed(raw))
    latest = newest_first[0]
    fmt_latest = _format_history_entry(latest)
    # Check if latest and second form a Sprint weekend pair (same base, one Sprint + one GP)
    if len(newest_first) >= 2:
        second = newest_first[1]
        n1, s1 = latest.get("normalized", ""), latest.get("session_type", "GP")
        n2, s2 = second.get("normalized", ""), second.get("session_type", "GP")
        if n1 == n2 and {s1, s2} == {"Sprint", "GP"}:
            fmt_second = _format_history_entry(second)
            sprint_evt = fmt_latest if fmt_latest["session_type"] == "Sprint" else fmt_second
            gp_evt = fmt_latest if fmt_latest["session_type"] == "GP" else fmt_second
            return [sprint_evt, gp_evt]
    return [fmt_latest]

def get_full_season_history():
    """Return full season history formatted for display, newest first."""
    _ensure_season_history_available()
    raw = load_season_results_history()
    return [_format_history_entry(e) for e in reversed(raw)]

def get_team_details(name, is_constructor=False):
    """Returns color, slug, and team name for a driver/constructor."""
    if is_constructor:
        team_name = name
    else:
        team_name = DRIVER_TEAM_MAP.get(name, "Cadillac")
    
    # Fuzzy match for team config
    config = get_team_config(team_name)
    return {
        "name": name,
        "team": team_name,
        "color": config['color'],
        "logo": f"https://media.formula1.com/content/dam/fom-website/teams/2024/{config['slug']}-logo.png.transform/2col/image.png",
        "car": f"https://media.formula1.com/d_team_car_fallback_image.png/content/dam/fom-website/teams/2024/{config['slug']}.png.transform/4col/image.png"
    }

def parse_picks(picks_str):
    """Parses the picks string into driver and constructor lists."""
    drivers = []
    constructors = []
    if pd.notna(picks_str):
        try:
            # Clean smart quotes
            raw_picks = str(picks_str).replace('“', '"').replace('”', '"').replace("‘", "'").replace("’", "'")
            picks_list = ast.literal_eval(raw_picks)
            
            # First 10 are drivers, rest are constructors
            for d in picks_list[:10]:
                drivers.append(get_team_details(d, is_constructor=False))
            for c in picks_list[10:]:
                constructors.append(get_team_details(c, is_constructor=True))
        except:
            pass
    return drivers, constructors

def get_next_session_info():
    """Calculates the countdown to the next F1 session."""
    try:
        if not os.path.exists('f1_cache'): os.makedirs('f1_cache')
        fastf1.Cache.enable_cache('f1_cache')
        now = datetime.datetime.now(datetime.timezone.utc)
        schedule = fastf1.get_event_schedule(now.year, include_testing=False)
        
        for _, event in schedule.iterrows():
            for i in range(1, 6):
                date_col = f'Session{i}DateUtc'
                name_col = f'Session{i}'
                if date_col in event and pd.notna(event[date_col]):
                    s_date = event[date_col]
                    if s_date.tzinfo is None: s_date = s_date.replace(tzinfo=datetime.timezone.utc)
                    if s_date > now:
                        return {
                            "name": f"{event['EventName']} - {event[name_col]}",
                            "date": s_date
                        }
    except:
        pass
    return None

def _session_display_type(session, results):
    """
    Classify session for display: 'qualifying' (Q/SQ times), 'race' (Time, Pts), or 'practice'.
    Avoids relying only on session.name; checks available columns.
    """
    if results is None or results.empty:
        return 'practice'
    cols = set(results.columns)
    session_name = (session.name or '').lower()
    if 'Q1' in cols or 'SQ1' in cols:
        return 'qualifying'
    if any(x in session_name for x in ['qualifying', 'sprint qualifying', 'sprint shootout']):
        return 'qualifying'
    if 'Time' in cols and 'Points' in cols:
        return 'race'
    if any(x in session_name for x in ['race', 'sprint']) and 'Time' not in cols:
        return 'race'
    return 'practice'


def _format_timedelta(td):
    """Format pd.Timedelta for display (e.g. '1:23.456')."""
    if td is None or pd.isna(td):
        return ""
    s = str(td)
    if 'days ' in s:
        s = s.split('days ')[-1]
    return s[:-3] if s.endswith('ns') else s


def _qualifying_time_cols(results):
    """Return timing column names for qualifying display: Q1/Q2/Q3 or SQ1/SQ2/SQ3."""
    cols = set(results.columns)
    if 'SQ1' in cols:
        return [c for c in ['SQ1', 'SQ2', 'SQ3'] if c in cols]
    return [c for c in ['Q1', 'Q2', 'Q3'] if c in cols]


def _resolve_position(row, display_index, display_type):
    """
    Resolve display position. Only treat as DNF for explicit non-position values.
    For qualifying fallback, use display_index (1-based numeric counter from enumerate).
    """
    NON_POSITION = {'nan', 'r', 'n/c', 'ret', 'none', '', 'dq', 'ex', 'd', 'e', 'w', 'f', 'n'}
    for col in ('Position', 'ClassifiedPosition', 'GridPosition'):
        val = row.get(col)
        if pd.isna(val) or val is None:
            continue
        pos = str(val).strip().lower()
        if pos in NON_POSITION:
            continue
        if pos.replace('.', '').replace('-', '').isdigit():
            p = str(val).strip()
            if p.endswith('.0'):
                p = p[:-2]
            return p
    if display_type == 'qualifying':
        return str(display_index)
    return "–"


def get_latest_results_data():
    """Fetches and formats the latest race/qualifying results."""
    try:
        if not os.path.exists('f1_cache'): os.makedirs('f1_cache')
        fastf1.Cache.enable_cache('f1_cache')
        
        now = datetime.datetime.now(datetime.timezone.utc)
        year = now.year
        schedule = fastf1.get_event_schedule(year, include_testing=False)
        
        # Fallback logic if early in year
        first_session = schedule['Session1DateUtc'].min() if not schedule.empty else None
        if first_session and first_session.tzinfo is None:
            first_session = first_session.replace(tzinfo=datetime.timezone.utc)
        
        if schedule.empty or (first_session and first_session > now):
            year -= 1
            schedule = fastf1.get_event_schedule(year, include_testing=False)
            
        # Find latest past session
        past_sessions = []
        for i, row in schedule.iterrows():
            for s_num in range(1, 6):
                date_col = f'Session{s_num}DateUtc'
                name_col = f'Session{s_num}'
                if date_col in row and pd.notna(row[date_col]):
                    s_date = row[date_col]
                    if s_date.tzinfo is None: s_date = s_date.replace(tzinfo=datetime.timezone.utc)
                    if s_date < now:
                        past_sessions.append({
                            'date': s_date,
                            'round': row['RoundNumber'],
                            'name': row[name_col],
                            'event': row['EventName']
                        })
        
        if not past_sessions: return None
        
        latest = sorted(past_sessions, key=lambda x: x['date'])[-1]
        session = fastf1.get_session(year, latest['round'], latest['name'])
        session.load(telemetry=False, weather=False, messages=False)
        
        results = session.results
        if results.empty: return None
        
        display_type = _session_display_type(session, results)
        data = []
        headers = ['Pos', 'Driver', 'Team']
        
        if display_type == 'qualifying':
            time_cols = _qualifying_time_cols(results)
            headers.extend(time_cols)
        elif display_type == 'race':
            headers.extend(['Time', 'Pts'])
        else:
            headers.extend(['Time', 'Pts'])
            
        for display_index, (_, row) in enumerate(results.iterrows(), start=1):
            # Color Logic
            team_name = row['TeamName']
            color = row.get('TeamColor', '')
            if pd.isna(color) or str(color).strip() == '':
                config = TEAM_CONFIG.get("Cadillac")
                for t_key, t_val in TEAM_CONFIG.items():
                    if t_key in str(team_name):
                        config = t_val
                        break
                color = config['color']
            else:
                if not str(color).startswith('#'): color = f"#{color}"
            
            text_color = '#ffffff'

            # Position Logic: only DNF when explicitly a non-position value
            pos = _resolve_position(row, display_index, display_type)
            if pos == "–" and display_type == 'race':
                val = str(row.get('Status', ''))
                if val and val.lower() not in ('', 'nan'):
                    pos = val
                else:
                    pos = "DNF"
            
            # Image Logic
            driver_name = row['FullName']
            img_url = get_driver_image(driver_name)
            if not img_url:
                img_url = f"https://ui-avatars.com/api/?name={driver_name}&background=fff&color={color.replace('#', '')}&size=128&bold=true"

            item = {'pos': pos, 'driver': driver_name, 'team': team_name, 'color': color, 'text_color': text_color, 'image': img_url, 'cols': []}
            
            if display_type == 'qualifying':
                time_cols = _qualifying_time_cols(results)
                for q in time_cols:
                    val = row.get(q, '')
                    item['cols'].append(_format_timedelta(val) if pd.notna(val) and str(val).strip() else "")
            else:
                time_val = row.get('Time')
                if pd.notna(time_val):
                    t = _format_timedelta(time_val)
                else:
                    t = str(row.get('Status', ''))
                pts = str(row.get('Points', 0)).replace('.0', '')
                item['cols'].extend([t, pts])
                
            data.append(item)
            
        return {"title": f"{session.event.EventName} - {session.name}", "headers": headers, "rows": data}
        
    except Exception as e:
        print(f"Error fetching results: {e}")
        return None

# --- ROUTES ---

@app.route('/')
def home():
    df = get_league_data()
    
    # Read Notice
    notice_msg = None
    if os.path.exists(NOTICE_FILE):
        with open(NOTICE_FILE, 'r') as f:
            notice_msg = f.read().strip()
            
    if df.empty:
        flash("Could not load league data.", "danger")
        return render_template('index.html', title="Home", leaderboard=[], current_weekend_events=[], notice=notice_msg)

    # 1. Current weekend event(s) for homepage (0, 1, or 2 tables)
    current_weekend_events = get_current_weekend_events()

    # 2. Main Leaderboard Data
    # Sort by official tie-break order (see scoring.LEADERBOARD_SORT_BY)
    sort_cols = [c for c in LEADERBOARD_SORT_BY if c in df.columns]
    sort_asc = [LEADERBOARD_SORT_ASCENDING[i] for i, c in enumerate(LEADERBOARD_SORT_BY) if c in df.columns]
    df = df.sort_values(by=sort_cols, ascending=sort_asc)
    
    leaderboard_data = []
    for i, (index, row) in enumerate(df.iterrows()):
        row_dict = row.to_dict()
        # Format Position: (Prev) Curr
        prev = int(row['Previous Pos']) if row['Previous Pos'] > 0 else "-"
        row_dict['DisplayPos'] = f"({prev}) {i + 1}"
        leaderboard_data.append(row_dict)

    return render_template('index.html', title="Leaderboard", leaderboard=leaderboard_data, current_weekend_events=current_weekend_events, notice=notice_msg)

@app.route('/season-history')
def season_history():
    """Full season event results history, newest first."""
    season_history_data = get_full_season_history()
    return render_template('season_history.html', title="Season History", season_history=season_history_data)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email').strip().lower()
        password = request.form.get('password')
        
        # Admin Override
        if email == "admin" and password == "admin12345":
            session['user'] = "Admin"
            flash("Welcome, Commissioner.", "success")
            return redirect(url_for('admin'))

        df = get_league_data()
        # Find user
        user_row = df[df['Email'].astype(str).str.strip().str.lower() == email]
        
        if not user_row.empty:
            stored_pw = str(user_row.iloc[0]['Password'])
            if stored_pw == password:
                session['user'] = user_row.iloc[0]['Nickname']
                session['email'] = email # Store email for lookup
                flash(f"Welcome back, {session['user']}!", "success")
                return redirect(url_for('my_team'))
            else:
                flash("Incorrect password.", "danger")
        else:
            flash("User not found.", "danger")
            
    return render_template('login.html', title="Login")

@app.route('/logout')
def logout():
    session.pop('user', None)
    flash("You have been logged out.", "info")
    return redirect(url_for('home'))

@app.route('/my-team')
def my_team():
    if 'user' not in session:
        flash("Please log in to view your team.", "warning")
        return redirect(url_for('login'))
    
    df = get_league_data()
    user_row = df[df['Nickname'] == session['user']]
    
    if user_row.empty:
        flash("User data not found.", "danger")
        return redirect(url_for('home'))
    
    user = user_row.iloc[0]
    drivers, constructors = parse_picks(user['Picks'])

    return render_template('dashboard.html', title="My Team", user=user, drivers=drivers, constructors=constructors)

@app.route('/team/<nickname>')
def view_team(nickname):
    df = get_league_data()
    user_row = df[df['Nickname'] == nickname]
    
    if user_row.empty:
        flash(f"Team '{nickname}' not found.", "danger")
        return redirect(url_for('home'))
    
    user = user_row.iloc[0]
    drivers, constructors = parse_picks(user['Picks'])
    return render_template('dashboard.html', title=f"{user['Nickname']}'s Team", user=user, drivers=drivers, constructors=constructors)

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        current_pw = request.form.get('current_password')
        new_pw = request.form.get('new_password')
        confirm_pw = request.form.get('confirm_password')
        
        if not all([current_pw, new_pw, confirm_pw]):
            flash("All password fields are required.", "danger")
        elif new_pw != confirm_pw:
            flash("New passwords do not match.", "danger")
        else:
            df = get_league_data()
            # Find user by nickname
            user_mask = df['Nickname'] == session['user']
            
            if not user_mask.any():
                if session['user'] == 'Admin':
                    flash("Admin password cannot be changed here.", "warning")
                else:
                    flash("User record not found.", "danger")
            else:
                user_idx = df.index[user_mask][0]
                stored_pw = str(df.at[user_idx, 'Password'])
                
                if stored_pw != current_pw:
                    flash("Current password is incorrect.", "danger")
                else:
                    df.at[user_idx, 'Password'] = new_pw
                    save_status = save_league_data(df)
                    if save_status is not False:
                        flash("Password updated successfully!", "success")
                        if save_status == 'skipped':
                            flash("Note: Changes saved locally. Google Sheet sync is inactive.", "info")
                    else:
                        flash("Error saving password to Google Sheets. Please try again.", "danger")

    return render_template('settings.html', title="Settings")

@app.route('/news')
def news():
    # 1. Countdown
    next_session = get_next_session_info()
    countdown = None
    if next_session:
        # Pass ISO format for JavaScript to handle real-time countdown
        countdown = {
            "name": next_session['name'],
            "target": next_session['date'].isoformat()
        }

    # 2. Latest Results
    results = get_latest_results_data()

    # 3. RSS Feed
    rss_url = "https://www.formula1.com/content/fom-website/en/latest/all.xml"
    feed = feedparser.parse(rss_url)
    articles = []
    if feed.entries:
        for entry in feed.entries[:10]:
            summary = entry.get('summary', '')
            # Clean summary
            summary = summary.replace("<br />", "\n").replace("<br>", "\n")
            summary = re.sub(r'<a\s+class="more".*?>.*?</a>', '', summary, flags=re.IGNORECASE)
            summary = re.sub(r'<[^>]+>', '', summary)
            articles.append({
                "title": entry.title, "link": entry.link, "summary": summary.strip()
            })

    return render_template('news.html', title="Latest News & Results", countdown=countdown, results=results, articles=articles)

@app.route('/standings')
def standings():
    # Fetch from Jolpica API (Ergast replacement)
    drivers = []
    constructors = []
    
    # Common headers and timestamp
    ts = int(datetime.datetime.now().timestamp())
    headers = {'User-Agent': 'F1-Fantasy-League/1.0'}
    
    # --- DRIVERS ---
    try:
        params = {'limit': 100, 't': ts}
        d_res = requests.get("https://api.jolpi.ca/ergast/f1/current/driverStandings.json", params=params, headers=headers, timeout=15)
        
        if d_res.status_code == 200:
            d_data = d_res.json().get('MRData', {}).get('StandingsTable', {}).get('StandingsLists', [])
            if d_data:
                for d in d_data[0].get('DriverStandings', []):
                    # Safe extraction to prevent crashes on missing data
                    driver_info = d.get('Driver', {})
                    name = f"{driver_info.get('givenName', '')} {driver_info.get('familyName', '')}"
                    
                    cons = d.get('Constructors', [])
                    team = cons[0].get('name', '-') if cons else "-"
                    
                    t_config = get_team_config(team)
                    
                    # Image Logic: Try official photo, fallback to avatar
                    img_url = get_driver_image(name)
                    if not img_url:
                        img_url = f"https://ui-avatars.com/api/?name={name}&background=fff&color={t_config['color'].replace('#', '')}&size=128&bold=true"
                    
                    drivers.append({
                        "pos": d.get('position', '-'),
                        "name": name,
                        "team": team,
                        "pts": d.get('points', '0'),
                        "color": t_config['color'],
                        "image": img_url
                    })
    except Exception as e:
        print(f"Drivers API Error: {e}")
        flash("Could not fetch Driver standings.", "warning")

    # --- CONSTRUCTORS ---
    try:
        params = {'limit': 100, 't': ts}
        c_res = requests.get("https://api.jolpi.ca/ergast/f1/current/constructorStandings.json", params=params, headers=headers, timeout=15)
        
        if c_res.status_code == 200:
            c_data = c_res.json().get('MRData', {}).get('StandingsTable', {}).get('StandingsLists', [])
            if c_data:
                for c in c_data[0].get('ConstructorStandings', []):
                    cons_info = c.get('Constructor', {})
                    team_name = cons_info.get('name', '-')
                    t_config = get_team_config(team_name)
                    
                    constructors.append({
                        "pos": c.get('position', '-'),
                        "team": team_name,
                        "pts": c.get('points', '0'),
                        "color": t_config['color']
                    })
    except Exception as e:
        print(f"Constructors API Error: {e}")
        flash("Could not fetch Constructor standings.", "warning")

    return render_template('standings.html', title="F1 Standings", drivers=drivers, constructors=constructors)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    # Countdown Logic
    current_year = datetime.datetime.now().year
    deadline = datetime.datetime(current_year, 3, 8, 5, 0)
    now = datetime.datetime.now()
    
    countdown_str = None
    signups_open = now < deadline
    
    if signups_open:
        time_left = deadline - now
        days = time_left.days
        hours, remainder = divmod(time_left.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        countdown_str = f"{days}d {hours}h {minutes}m"

    if request.method == 'POST':
        # 1. Gather Personal Info
        name = request.form.get('name')
        nickname = request.form.get('nickname')
        email = request.form.get('email')
        password = request.form.get('password')
        rules_check = request.form.get('rules')

        # 2. Gather Picks
        # Checkboxes (Pick 2)
        g_a = [x for x in request.form.getlist('g_a') if x]
        g_b = [x for x in request.form.getlist('g_b') if x]
        g_i = [x for x in request.form.getlist('g_i') if x]
        
        # Selects (Pick 1)
        g_c = request.form.get('g_c')
        g_d = request.form.get('g_d')
        g_e = request.form.get('g_e')
        g_f = request.form.get('g_f')
        g_g = request.form.get('g_g')
        g_h = request.form.get('g_h')
        g_j = request.form.get('g_j')
        g_k = request.form.get('g_k')
        g_l = request.form.get('g_l')
        g_m = request.form.get('g_m')

        # 3. Validation
        errors = []
        if not rules_check: errors.append("You must agree to the rules.")
        if not all([name, nickname, email, password]): errors.append("All personal fields are required.")
        
        if len(g_a) != 2: errors.append(f"Group A: Select exactly 2 (got {len(g_a)}).")
        if len(g_b) != 2: errors.append(f"Group B: Select exactly 2 (got {len(g_b)}).")
        if len(g_i) != 2: errors.append(f"Group I: Select exactly 2 (got {len(g_i)}).")
        
        singles = [g_c, g_d, g_e, g_f, g_g, g_h, g_j, g_k, g_l, g_m]
        if not all(singles): errors.append("Please make a selection for every group.")

        all_picks = g_a + g_b + [g_c, g_d, g_e, g_f, g_g, g_h] + g_i + [g_j, g_k, g_l, g_m]
        constructors = all_picks[10:]
        seen_ff1 = {}
        for c in constructors:
            ff1 = app_constructor_to_fastf1(c)
            if ff1 in seen_ff1:
                errors.append(f"Cannot pick both '{c}' and '{seen_ff1[ff1]}' — they map to the same team ({ff1}).")
                break
            seen_ff1[ff1] = c

        if errors:
            for e in errors: flash(e, "danger")
        else:
            # 4. Duplicate Check
            
            df = get_league_data()
            new_picks_set = set(all_picks)
            
            if not df.empty and 'Picks' in df.columns:
                for _, row in df.iterrows():
                    if pd.notna(row['Picks']):
                        try:
                            clean_picks = str(row['Picks']).replace('“', '"').replace('”', '"').replace("‘", "'").replace("’", "'")
                            existing_picks = ast.literal_eval(clean_picks)
                            if set(existing_picks) == new_picks_set:
                                flash(f"Team already exists! Chosen by '{row['Name']}'. Change at least 1 pick.", "danger")
                                return redirect(url_for('signup'))
                        except: continue
            
            # 5. Save
            new_row = {"Name": name, "Nickname": nickname, "Email": email, "Password": password, "Picks": str(all_picks), "Current Score": 0, "Total Winnings": 0, "Pos": 0, "Previous Pos": 0, "Last Race Pts": 0, "Total Spent": 0}
            updated_df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True) if not df.empty else pd.DataFrame([new_row])
            save_status = save_league_data(updated_df)
            flash("✅ Registration successful! Good luck!", "success")
            if save_status == 'skipped':
                flash("Your registration is saved locally. The commissioner will sync it to the master sheet.", "info")
            elif save_status is False:
                flash("❌ Registration saved locally, but failed to sync to the Google Sheet. Please contact the commissioner.", "danger")
            return redirect(url_for('home'))

    return render_template('signup.html', title="Signup", countdown=countdown_str, open=signups_open)

@app.route('/admin')
def admin():
    # Security check (simple version)
    if 'user' not in session:
        flash("Access denied. Please log in.", "danger")
        return redirect(url_for('login'))
    
    if session['user'] != "Admin":
        flash("Access denied. Commissioner privileges required.", "danger")
        return redirect(url_for('home'))

    races = [
        "Australia", "China", "China Sprint", "Japan", "Bahrain", "Saudi Arabia",
        "Miami", "Miami Sprint", "Emilia Romagna", "Monaco", "Barcelona-Catalunya", "Spain",
        "Canada", "Canada Sprint", "Austria", "Great Britain", "Great Britain Sprint", "Belgium",
        "Hungary", "Netherlands", "Netherlands Sprint", "Italy", "Azerbaijan", "Singapore", "Singapore Sprint",
        "United States", "Mexico City", "Brazil", "Las Vegas", "Qatar", "Abu Dhabi"
    ]
    
    # Read current notice for editing
    current_notice = ""
    if os.path.exists(NOTICE_FILE):
        with open(NOTICE_FILE, 'r') as f:
            current_notice = f.read().strip()
            
    # Check connection status
    google_sync_status = get_gspread_client() is not None
    
    # Get last data update time
    last_update = "Never"
    if os.path.exists(DATA_FILE):
        timestamp = os.path.getmtime(DATA_FILE)
        last_update = datetime.datetime.fromtimestamp(timestamp).strftime('%d %b %Y, %H:%M:%S')

    # Build test leaderboard (sorted, with positions)
    test_df = get_test_league_data()
    if not test_df.empty:
        sort_cols = [c for c in LEADERBOARD_SORT_BY if c in test_df.columns]
        sort_asc = [LEADERBOARD_SORT_ASCENDING[i] for i, c in enumerate(LEADERBOARD_SORT_BY) if c in test_df.columns]
        test_df = test_df.sort_values(by=sort_cols, ascending=sort_asc)
        test_df = test_df.copy()
        test_df['Pos'] = test_df['Current Score'].rank(ascending=False, method='min').fillna(0).astype(int)
        display_cols = [c for c in ['Pos', 'Name', 'Nickname', 'Current Score', 'Last Race Pts', 'Total Winnings', 'Total Spent'] if c in test_df.columns]
        test_leaderboard = test_df[display_cols].to_dict('records')
    else:
        test_leaderboard = []

    recent_synced = get_recent_synced_events(10)

    # Build player list for Debug Score Team (from production league data only)
    # Use row index as value for unambiguous lookup; leaderboard uses same get_league_data()
    df_league = get_league_data()
    players = []
    if not df_league.empty:
        for idx, row in df_league.iterrows():
            nickname = str(row.get('Nickname', '')).strip() or str(row.get('Name', ''))
            name = str(row.get('Name', '')).strip()
            email = str(row.get('Email', '')).strip()
            label = f"{nickname} ({name})" if nickname and name and nickname != name else (nickname or name or email or f"Row {idx}")
            players.append({"index": idx, "label": label})
        players.sort(key=lambda p: (p["label"].lower(), p["index"]))

    debug_result = session.pop('debug_result', None)

    return render_template('admin.html', title="Admin", races=races, notice=current_notice, google_sync_status=google_sync_status, last_update=last_update, test_leaderboard=test_leaderboard, recent_synced=recent_synced, players=players, debug_result=debug_result)

@app.route('/admin/notice', methods=['POST'])
def admin_notice():
    if 'user' not in session or session['user'] != "Admin":
        return redirect(url_for('home'))
        
    msg = request.form.get('notice_msg', '')
    try:
        with open(NOTICE_FILE, 'w') as f:
            f.write(msg)
        flash("Notice updated successfully.", "success")
    except Exception as e:
        flash(f"Error updating notice: {e}", "danger")
        
    return redirect(url_for('admin'))

@app.route('/admin/export')
def admin_export():
    if 'user' not in session or session['user'] != "Admin":
        return redirect(url_for('home'))
    
    if os.path.exists(DATA_FILE):
        return send_file(DATA_FILE, as_attachment=True, download_name=f"f1_fantasy_backup_{datetime.datetime.now().strftime('%Y%m%d')}.csv")
    else:
        flash("No data file found to export.", "warning")
        return redirect(url_for('admin'))

@app.route('/admin/clear_cache', methods=['POST'])
def admin_clear_cache():
    if 'user' not in session or session['user'] != "Admin":
        return redirect(url_for('home'))
    
    try:
        # Disable cache to release file locks (Windows fix)
        fastf1.Cache.set_disabled()
        if os.path.exists('f1_cache'):
            shutil.rmtree('f1_cache')
        flash("✅ System cache cleared! FastF1 will re-download fresh data on next request.", "success")
    except Exception as e:
        flash(f"Error clearing cache: {e}", "danger")
        
    return redirect(url_for('admin'))

@app.route('/admin/pull_sheet')
def admin_pull_sheet():
    if 'user' not in session or session['user'] != "Admin":
        return redirect(url_for('home'))
    
    df = fetch_google_sheet_data()
    if not df.empty:
        save_league_data(df)
        flash("✅ Successfully pulled latest data from Google Sheet.", "success")
    else:
        flash("❌ Failed to fetch data from Google Sheet.", "danger")
    return redirect(url_for('admin'))

@app.route('/admin/reset_scores', methods=['POST'])
def admin_reset_scores():
    if 'user' not in session or session['user'] != "Admin":
        return redirect(url_for('home'))
        
    df = get_league_data()
    if not df.empty:
        # Reset scoring columns to 0 (999 for Best Finish cols), keep Name/Picks/Email/Password
        for c in ['Current Score', 'Total Winnings', 'Pos', 'Previous Pos', 'Last Race Pts', 'Total Spent',
                  'Driver Race Pts', 'Constructor Race Pts', 'Top Driver Score']:
            if c in df.columns:
                df[c] = 0
        for c in ['Best Finish Pos', 'Prior Best Finish Pos']:
            if c in df.columns:
                df[c] = 999
        save_league_data(df)
        flash("✅ Season scores and stats have been reset to 0. Teams are preserved.", "success")
    
    return redirect(url_for('admin'))

@app.route('/admin/reset', methods=['POST'])
def admin_reset():
    if 'user' not in session or session['user'] != "Admin":
        return redirect(url_for('home'))
        
    # Reset with specific columns matching the schema
    cols = ['Name', 'Nickname', 'Email', 'Password', 'Picks', 'Current Score',
            'Total Winnings', 'Pos', 'Previous Pos', 'Last Race Pts', 'Total Spent',
            'Driver Race Pts', 'Constructor Race Pts', 'Top Driver Score', 'Best Finish Pos', 'Prior Best Finish Pos']
    df = pd.DataFrame(columns=cols)
    save_league_data(df)
    flash("⚠️ League data has been completely wiped.", "warning")
    return redirect(url_for('admin'))

@app.route('/admin/sync', methods=['POST'])
def admin_sync():
    if 'user' not in session or session['user'] != "Admin":
        flash("Access denied.", "danger")
        return redirect(url_for('home'))
        
    action = request.form.get('action')
    
    if action == 'sync':
        race_name = (request.form.get('race_name') or "").strip()
        if not race_name:
            flash("PRODUCTION MODE: No race selected.", "danger")
            return redirect(url_for('admin'))

        # 1. Duplicate sync protection
        if is_event_already_synced(race_name):
            flash(f"PRODUCTION MODE: {race_name} has already been synced. Duplicate sync blocked.", "warning")
            return redirect(url_for('admin'))

        # 2. Sprint-before-GP validation (GP on Sprint weekend must have Sprint synced first)
        if is_gp_on_sprint_weekend(race_name) and not sprint_already_synced_for_gp(race_name):
            base = normalize_event_name(race_name)
            flash(f"PRODUCTION MODE: {base} Grand Prix cannot be synced before {base} Sprint has been synced.", "warning")
            return redirect(url_for('admin'))

        df = get_league_data()
        try:
            p1 = float(request.form.get('p1', 0))
            p2 = float(request.form.get('p2', 0))
            p3 = float(request.form.get('p3', 0))
            p_rest = float(request.form.get('p_rest', 0))
            payouts = [p1, p2, p3] + [p_rest] * 12
        except ValueError:
            flash("Invalid payout values.", "danger")
            return redirect(url_for('admin'))

        updated_df, msg = scoring.calculate_race_scores(df, LEAGUE_YEAR, race_name, payouts)
        
        if "Successfully" in msg:
            save_status = save_league_data(updated_df)
            if save_status is True:
                flash(f"PRODUCTION MODE: {msg} Data synced to CSV and Google Sheet.", "success")
            elif save_status == 'skipped':
                flash(f"PRODUCTION MODE: {msg} (Local save only. Google Sheet sync is inactive.)", "warning")
            else:
                flash(f"PRODUCTION MODE: {msg} Google Sheet sync failed.", "danger")
            session_type = "Sprint" if is_sprint_event(race_name) else "GP"
            add_sync_to_history(race_name, session_type)
            add_event_to_season_history(race_name, session_type, updated_df)
        else:
            flash(msg, "danger")

    elif action == 'force_sync':
        race_name = (request.form.get('race_name') or "").strip()
        if not race_name:
            flash("PRODUCTION MODE: No race selected.", "danger")
            return redirect(url_for('admin'))

        # Bypass duplicate check; still enforce Sprint-before-GP
        if is_gp_on_sprint_weekend(race_name) and not sprint_already_synced_for_gp(race_name):
            base = normalize_event_name(race_name)
            flash(f"PRODUCTION MODE: {base} Grand Prix cannot be resynced before {base} Sprint has been synced.", "warning")
            return redirect(url_for('admin'))

        try:
            p1 = float(request.form.get('p1', 0))
            p2 = float(request.form.get('p2', 0))
            p3 = float(request.form.get('p3', 0))
            p_rest = float(request.form.get('p_rest', 0))
            force_payouts = [p1, p2, p3] + [p_rest] * 12
        except ValueError:
            flash("Invalid payout values.", "danger")
            return redirect(url_for('admin'))

        default_payouts = [20, 15, 10] + [5] * 12
        year = LEAGUE_YEAR

        # Rebuild season from history to correctly overwrite (no double-count)
        df = get_league_data()
        for c in ['Current Score', 'Total Winnings', 'Previous Pos', 'Last Race Pts', 'Total Spent',
                  'Driver Race Pts', 'Constructor Race Pts', 'Top Driver Score']:
            if c in df.columns:
                df[c] = 0
        for c in ['Best Finish Pos', 'Prior Best Finish Pos']:
            if c in df.columns:
                df[c] = 999

        history = load_sync_history()
        last_msg = ""
        new_season_history = []
        for entry in history:
            evt = (entry.get("event_name") or "").strip()
            payouts = force_payouts if evt == race_name else default_payouts
            df, msg = scoring.calculate_race_scores(df, year, evt, payouts)
            if "Successfully" not in msg:
                flash(f"PRODUCTION MODE: Force resync failed during rebuild: {msg}", "danger")
                return redirect(url_for('admin'))
            if evt == race_name:
                last_msg = msg
            sess_type = entry.get("session_type", "GP")
            append_event_snapshot_to_history(new_season_history, evt, sess_type, df)

        save_season_results_history(new_season_history)
        save_status = save_league_data(df)
        if save_status is True:
            flash(f"PRODUCTION MODE: Force resync complete. {last_msg} Data synced to CSV and Google Sheet.", "success")
        elif save_status == 'skipped':
            flash(f"PRODUCTION MODE: Force resync complete. {last_msg} (Local save only. Google Sheet sync is inactive.)", "warning")
        else:
            flash(f"PRODUCTION MODE: Force resync complete. {last_msg} Google Sheet sync failed.", "danger")
        session_type = "Sprint" if is_sprint_event(race_name) else "GP"
        update_sync_in_history(race_name, session_type)

    elif action == 'test':
        df = get_test_league_data()
        test_payouts = [20, 15, 10] + [5] * 9
        updated_df, msg = scoring.calculate_race_scores(df, LEAGUE_YEAR, "Test Race", test_payouts, is_test=True)
        if "Successfully" in msg:
            save_test_league_data(updated_df)
            flash(f"TEST MODE: {msg} Test leaderboard updated (production untouched).", "success")
        else:
            flash(msg, "danger")

    elif action == 'test_sprint':
        df = get_test_league_data()
        test_payouts = [20, 15, 10] + [5] * 9
        updated_df, msg = scoring.calculate_race_scores(df, LEAGUE_YEAR, "Test Sprint", test_payouts, is_test='sprint')
        if "Successfully" in msg:
            save_test_league_data(updated_df)
            flash(f"TEST MODE: {msg} Test leaderboard updated (production untouched).", "success")
        else:
            flash(msg, "danger")

    elif action == 'reset_test_data':
        reset_test_league_data()
        flash("TEST MODE: Test leaderboard reset from current production data. Production untouched.", "success")

    return redirect(url_for('admin'))


@app.route('/admin/debug_score', methods=['POST'])
def admin_debug_score():
    """Read-only: debug scoring for a selected player's picks. No writes to league/test data or Google Sheets."""
    if 'user' not in session or session['user'] != "Admin":
        flash("Access denied.", "danger")
        return redirect(url_for('admin'))

    race_name = (request.form.get('debug_race_name') or "").strip()
    player_index_str = (request.form.get('player_index') or "").strip()
    debug_mode = (request.form.get('debug_mode') or "current_season").strip()

    if not race_name:
        flash("Debug: No race selected.", "warning")
        return redirect(url_for('admin'))

    if not player_index_str:
        flash("Debug: No player selected.", "warning")
        return redirect(url_for('admin'))

    df = get_league_data()
    if df.empty:
        flash("Debug: No league data available.", "danger")
        return redirect(url_for('admin'))

    try:
        player_index = int(player_index_str)
    except ValueError:
        flash("Debug: Invalid player selection.", "danger")
        return redirect(url_for('admin'))

    if player_index not in df.index:
        flash("Debug: Player not found (row no longer exists).", "danger")
        return redirect(url_for('admin'))

    row = df.loc[player_index]
    picks_str = row.get('Picks')
    picks = parse_picks_from_string(picks_str)
    if not picks or len(picks) < 11:
        flash("Debug: Player has no valid picks stored.", "danger")
        return redirect(url_for('admin'))

    is_test = False
    if debug_mode == 'gp_test':
        is_test = True
    elif debug_mode == 'sprint_test':
        is_test = 'sprint'

    result = get_team_scoring_breakdown(picks, LEAGUE_YEAR, race_name, is_test=is_test)
    if "error" in result:
        flash(f"Debug: {result['error']}", "danger")
        return redirect(url_for('admin'))

    nickname = str(row.get('Nickname', '')).strip() or str(row.get('Name', ''))
    name = str(row.get('Name', '')).strip()
    result['player_label'] = nickname
    result['debug_confirmation'] = {
        "player_index": player_index,
        "nickname": nickname,
        "name": name,
        "picks_loaded": picks,
    }
    session['debug_result'] = result
    return redirect(url_for('admin'))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)