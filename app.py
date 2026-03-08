from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
import datetime
import pandas as pd
import ast
import requests
import feedparser
import os
import scoring
import fastf1
import re
import gspread

app = Flask(__name__)
app.secret_key = "dev_key_f1_2026"  # Required for session and flash messages

# Inject 'year' into all templates automatically
@app.context_processor
def inject_globals():
    return {
        'year': datetime.datetime.now().year,
        'now': datetime.datetime.now()
    }

# --- CONFIGURATION & DATA HELPERS ---

SHEET_ID = "150YSDU3o1SiEM1WHpPEK9pNPnGUu03qxR26H77RnApw"
SHEET_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"
DATA_FILE = 'league_data.csv'
NOTICE_FILE = 'notice.txt'
CREDENTIALS_FILE = 'service_account.json.json'

TEAM_CONFIG = {
    "Ferrari": {"color": "#E80020", "slug": "ferrari"},
    "McLaren": {"color": "#FF8000", "slug": "mclaren"},
    "Mercedes": {"color": "#27F4D2", "slug": "mercedes"},
    "Red Bull": {"color": "#3671C6", "slug": "red-bull-racing"},
    "Aston Martin": {"color": "#229971", "slug": "aston-martin"},
    "Alpine": {"color": "#0093CC", "slug": "alpine"},
    "Williams": {"color": "#64C4FF", "slug": "williams"},
    "Racing Bulls": {"color": "#6692FF", "slug": "rb"},
    "Haas": {"color": "#B6BABD", "slug": "haas-f1-team"},
    "Audi": {"color": "#52E252", "slug": "kick-sauber"},
    "Cadillac": {"color": "#FFD700", "slug": "f1"},
}

DRIVER_TEAM_MAP = {
    "Charles Leclerc": "Ferrari", "Lewis Hamilton": "Ferrari",
    "George Russell": "Mercedes", "Kimi Antonelli": "Mercedes",
    "Lando Norris": "McLaren", "Oscar Piastri": "McLaren",
    "Max Verstappen": "Red Bull", "Sergio Perez": "Red Bull", "Liam Lawson": "Red Bull",
    "Fernando Alonso": "Aston Martin", "Lance Stroll": "Aston Martin",
    "Pierre Gasly": "Alpine", "Jack Doohan": "Alpine",
    "Alex Albon": "Williams", "Carlos Sainz Jnr": "Williams", "Franco Colapinto": "Williams",
    "Esteban Ocon": "Haas", "Oliver Bearman": "Haas",
    "Nico Hulkenberg": "Audi", "Gabriel Bortoleto": "Audi", "Valtteri Bottas": "Audi",
    "Isack Hadjar": "Racing Bulls", "Arvid Lindblad": "Racing Bulls", "Yuki Tsunoda": "Racing Bulls"
}

def fetch_google_sheet_data():
    """Attempts to fetch data from Google Sheets via API or CSV Export."""
    df = pd.DataFrame()
    # 1. Try API (gspread) - Best for private sheets
    if os.path.exists(CREDENTIALS_FILE):
        try:
            gc = gspread.service_account(filename=CREDENTIALS_FILE)
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

    # Ensure numeric columns exist
    cols = ['Current Score', 'Total Winnings', 'Previous Pos', 'Last Race Pts', 'Total Spent']
    for c in cols:
        if c not in df.columns:
            df[c] = 0
        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
        
    return df

def save_league_data(df):
    """Saves to local CSV and attempts to sync to Google Sheet."""
    # 1. Save Local
    df.to_csv(DATA_FILE, index=False)
    
    # 2. Try Google Sheet Sync (Push)
    if os.path.exists(CREDENTIALS_FILE):
        try:
            gc = gspread.service_account(filename=CREDENTIALS_FILE)
            sh = gc.open_by_key(SHEET_ID)
            ws = sh.sheet1
            # Convert to list of lists, handling NaNs and types for Sheets
            # We use fillna('') because Sheets doesn't like NaN
            data = [df.columns.values.tolist()] + df.fillna('').astype(str).values.tolist()
            ws.clear()
            ws.update(range_name='A1', values=data)
            print("Synced to Google Sheet")
        except Exception as e:
            print(f"Google Sheet Sync Failed: {e}")
    else:
        print(f"⚠️ Skipping Google Sheet Sync: '{CREDENTIALS_FILE}' not found. Data saved locally only.")

def get_team_details(name, is_constructor=False):
    """Returns color, slug, and team name for a driver/constructor."""
    if is_constructor:
        team_name = name
    else:
        team_name = DRIVER_TEAM_MAP.get(name, "Cadillac")
    
    # Fuzzy match for team config
    config = TEAM_CONFIG.get("Cadillac")
    for t_key, t_val in TEAM_CONFIG.items():
        if t_key in team_name:
            config = t_val
            team_name = t_key
            break
            
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
        
        # Process Data
        data = []
        headers = ['Pos', 'Driver', 'Team']
        
        is_quali = 'Q3' in results.columns
        if is_quali:
            headers.extend(['Q1', 'Q2', 'Q3'])
        elif 'Time' in results.columns:
            headers.extend(['Time', 'Pts'])
            
        for idx, row in results.iterrows():
            # Color Logic
            team_name = row['TeamName']
            color = row.get('TeamColor', '')
            if pd.isna(color) or str(color).strip() == '':
                # Fallback colors
                config = TEAM_CONFIG.get("Cadillac") # Default
                for t_key, t_val in TEAM_CONFIG.items():
                    if t_key in str(team_name):
                        config = t_val
                        break
                color = config['color']
            else:
                if not str(color).startswith('#'): color = f"#{color}"
            
            # Text Contrast
            text_color = '#ffffff' # Default white text

            # Position Logic
            val = row.get('Position')
            if pd.isna(val):
                val = row.get('ClassifiedPosition')
            
            pos = str(val).strip()
            if pos.endswith('.0'):
                pos = pos[:-2]
                
            if pos.lower() in ['nan', 'r', 'n/c', 'ret', 'none', '', 'dq', 'ex']:
                pos = "DNF"
            
            item = {'pos': pos, 'driver': row['FullName'], 'team': team_name, 'color': color, 'text_color': text_color, 'cols': []}
            
            if is_quali:
                for q in ['Q1', 'Q2', 'Q3']:
                    val = str(row.get(q, '')).split('days ')[-1][:-3] if pd.notna(row.get(q, '')) and str(row.get(q, '')).strip() != "" else ""
                    item['cols'].append(val)
            else:
                t = str(row.get('Time', '')).split('days ')[-1][:-3] if pd.notna(row.get('Time', '')) else str(row.get('Status', ''))
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
        return render_template('index.html', title="Home", leaderboard=[], top_scorers=[], top_earners=[], notice=notice_msg)
    
    # 1. Latest Race Recap Data
    top_scorers = df.sort_values(by='Last Race Pts', ascending=False).head(5)[['Nickname', 'Last Race Pts']].to_dict(orient='records')
    top_earners = df[df['Total Winnings'] > 0].sort_values(by='Total Winnings', ascending=False).head(5)[['Nickname', 'Total Winnings']].to_dict(orient='records')
    
    # 2. Main Leaderboard Data
    df = df.sort_values(by=['Current Score', 'Total Winnings'], ascending=False)
    
    leaderboard_data = []
    for i, (index, row) in enumerate(df.iterrows()):
        row_dict = row.to_dict()
        # Format Position: (Prev) Curr
        prev = int(row['Previous Pos']) if row['Previous Pos'] > 0 else "-"
        row_dict['DisplayPos'] = f"({prev}) {i + 1}"
        leaderboard_data.append(row_dict)

    return render_template('index.html', title="Leaderboard", leaderboard=leaderboard_data, top_scorers=top_scorers, top_earners=top_earners, notice=notice_msg)

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
    return render_template('dashboard.html', title="My Team", user=user, drivers=drivers, constructors=constructors)

@app.route('/news')
def news():
    # 1. Countdown
    next_session = get_next_session_info()
    countdown = None
    if next_session:
        delta = next_session['date'] - datetime.datetime.now(datetime.timezone.utc)
        days = delta.days
        hours, rem = divmod(delta.seconds, 3600)
        mins, _ = divmod(rem, 60)
        countdown = {
            "name": next_session['name'],
            "time": f"{days}d {hours}h {mins}m"
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
    
    try:
        # Drivers
        d_res = requests.get("https://api.jolpi.ca/ergast/f1/current/driverStandings.json", timeout=2)
        if d_res.status_code == 200:
            d_data = d_res.json()['MRData']['StandingsTable']['StandingsLists']
            if d_data:
                for d in d_data[0]['DriverStandings']:
                    drivers.append({
                        "pos": d['position'],
                        "name": f"{d['Driver']['givenName']} {d['Driver']['familyName']}",
                        "team": d['Constructors'][0]['name'] if d['Constructors'] else "-",
                        "pts": d['points']
                    })
        
        # Constructors
        c_res = requests.get("https://api.jolpi.ca/ergast/f1/current/constructorStandings.json", timeout=2)
        if c_res.status_code == 200:
            c_data = c_res.json()['MRData']['StandingsTable']['StandingsLists']
            if c_data:
                for c in c_data[0]['ConstructorStandings']:
                    constructors.append({
                        "pos": c['position'],
                        "team": c['Constructor']['name'],
                        "pts": c['points']
                    })
    except Exception as e:
        print(f"API Error: {e}")
        flash("Could not fetch live F1 standings.", "warning")

    return render_template('standings.html', title="Standings", drivers=drivers, constructors=constructors)

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
        if not signups_open:
            flash("Signups are closed for this season.", "danger")
            return redirect(url_for('signup'))

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

        if errors:
            for e in errors: flash(e, "danger")
        else:
            # 4. Duplicate Check
            all_picks = g_a + g_b + [g_c, g_d, g_e, g_f, g_g, g_h] + g_i + [g_j, g_k, g_l, g_m]
            
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
            save_league_data(updated_df)
            flash("✅ Registration successful! Good luck!", "success")
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
        "Australia", "China", "Japan", "Bahrain", "Saudi Arabia", "Miami", 
        "Canada", "Monaco", "Barcelona-Catalunya", "Austria", "Great Britain", 
        "Belgium", "Hungary", "Netherlands", "Italy", "Spain", "Azerbaijan", 
        "Singapore", "United States", "Mexico City", "Brazil", "Las Vegas", 
        "Qatar", "Abu Dhabi"
    ]
    
    # Read current notice for editing
    current_notice = ""
    if os.path.exists(NOTICE_FILE):
        with open(NOTICE_FILE, 'r') as f:
            current_notice = f.read().strip()
            
    # Check connection status
    google_sync_status = os.path.exists(CREDENTIALS_FILE)
            
    return render_template('admin.html', title="Admin", races=races, notice=current_notice, google_sync_status=google_sync_status)

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
        # Reset scoring columns to 0, keep Name/Picks/Email/Password
        cols = ['Current Score', 'Total Winnings', 'Pos', 'Previous Pos', 'Last Race Pts', 'Total Spent']
        for c in cols:
            df[c] = 0
        save_league_data(df)
        flash("✅ Season scores and stats have been reset to 0. Teams are preserved.", "success")
    
    return redirect(url_for('admin'))

@app.route('/admin/reset', methods=['POST'])
def admin_reset():
    if 'user' not in session or session['user'] != "Admin":
        return redirect(url_for('home'))
        
    # Reset with specific columns matching the schema
    cols = ['Name', 'Nickname', 'Email', 'Password', 'Picks', 'Current Score', 
            'Total Winnings', 'Pos', 'Previous Pos', 'Last Race Pts', 'Total Spent']
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
    df = get_league_data()
    
    if action == 'sync':
        race_name = request.form.get('race_name')
        try:
            p1 = float(request.form.get('p1', 0))
            p2 = float(request.form.get('p2', 0))
            p3 = float(request.form.get('p3', 0))
            p_rest = float(request.form.get('p_rest', 0))
            payouts = [p1, p2, p3] + [p_rest] * 9
        except ValueError:
            flash("Invalid payout values.", "danger")
            return redirect(url_for('admin'))

        updated_df, msg = scoring.calculate_race_scores(df, datetime.datetime.now().year, race_name, payouts)
        
        if "Successfully" in msg:
            save_league_data(updated_df)
            flash(msg, "success")
        else:
            flash(msg, "danger")
            
    elif action == 'test':
        test_payouts = [20, 15, 10] + [5] * 9
        updated_df, msg = scoring.calculate_race_scores(df, datetime.datetime.now().year, "Test Race", test_payouts, is_test=True)
        if "Successfully" in msg:
            save_league_data(updated_df)
            flash("Test race simulation successful! Data updated.", "success")
        else:
            flash(msg, "danger")
            
    return redirect(url_for('admin'))

if __name__ == "__main__":
    app.run(debug=True)