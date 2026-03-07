from flask import Flask, render_template, request, redirect, url_for, session, flash
import datetime
import pandas as pd
import ast
import requests
import feedparser
import os
import scoring

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

def get_league_data():
    """Fetches data from local CSV or falls back to Google Sheet export."""
    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE)
    else:
        try:
            df = pd.read_csv(SHEET_URL)
            # Clean numeric columns
            cols = ['Current Score', 'Total Winnings', 'Previous Pos', 'Last Race Pts', 'Total Spent']
            for c in cols:
                if c in df.columns:
                    df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
            
            # Save locally for persistence
            df.to_csv(DATA_FILE, index=False)
            return df
        except Exception as e:
            print(f"Data Fetch Error: {e}")
            return pd.DataFrame()

def save_league_data(df):
    """Saves the DataFrame to the local CSV file."""
    df.to_csv(DATA_FILE, index=False)

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

# --- ROUTES ---

@app.route('/')
def home():
    df = get_league_data()
    if df.empty:
        flash("Could not load league data.", "danger")
        return render_template('index.html', title="Home", leaderboard=[], top_scorers=[], top_earners=[])
    
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

    return render_template('index.html', title="Leaderboard", leaderboard=leaderboard_data, top_scorers=top_scorers, top_earners=top_earners)

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
    # Fetch RSS Feed
    rss_url = "https://www.formula1.com/content/fom-website/en/latest/all.xml"
    feed = feedparser.parse(rss_url)
    articles = feed.entries[:10] if feed.entries else []
    return render_template('news.html', title="News", articles=articles)

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
    if request.method == 'POST':
        # In a real app, you would write to the Google Sheet here using gspread.
        # Since we are using read_csv (read-only) for simplicity, we show a message.
        flash("Signup is currently disabled in this local version. (Requires Google Sheets API Write Access)", "info")
        return redirect(url_for('home'))
        
    return render_template('signup.html', title="Signup")

@app.route('/admin')
def admin():
    # Security check (simple version)
    if 'user' not in session:
        flash("Access denied. Please log in.", "danger")
        return redirect(url_for('login'))

    races = [
        "Australia", "China", "Japan", "Bahrain", "Saudi Arabia", "Miami", 
        "Canada", "Monaco", "Barcelona-Catalunya", "Austria", "Great Britain", 
        "Belgium", "Hungary", "Netherlands", "Italy", "Spain", "Azerbaijan", 
        "Singapore", "United States", "Mexico City", "Brazil", "Las Vegas", 
        "Qatar", "Abu Dhabi"
    ]
    return render_template('admin.html', title="Admin", races=races)

@app.route('/admin/sync', methods=['POST'])
def admin_sync():
    if 'user' not in session:
        return redirect(url_for('login'))
        
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