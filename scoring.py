import fastf1
import pandas as pd
import os
import ast
import random

# Cache setup for fast loading
if not os.path.exists('f1_cache'):
    os.makedirs('f1_cache')
fastf1.Cache.enable_cache('f1_cache') 

DRIVER_MAP = {
    "Charles Leclerc": "LEC", "George Russell": "RUS", "Lando Norris": "NOR",
    "Max Verstappen": "VER", "Fernando Alonso": "ALO", "Kimi Antonelli": "ANT",
    "Lewis Hamilton": "HAM", "Oscar Piastri": "PIA", "Carlos Sainz Jnr": "SAI",
    "Isack Hadjar": "HAD", "Pierre Gasly": "GAS", "Alex Albon": "ALB",
    "Lance Stroll": "STR", "Esteban Ocon": "OCO", "Liam Lawson": "LAW",
    "Oliver Bearman": "BEA", "Arvid Lindblad": "LIN", "Nico Hulkenberg": "HUL",
    "Franco Colapinto": "COL", "Gabriel Bortoleto": "BOR", "Sergio Perez": "PER",
    "Valtteri Bottas": "BOT"
}

# Map your App's team names to FastF1's official team names
CONSTRUCTOR_MAP = {
    "Red Bull": "Red Bull Racing",
    "Racing Bulls": "RB",
    "Haas": "Haas F1 Team",
    "Audi": "Kick Sauber", # Placeholder for testing with 2024 data
    "Cadillac": "Williams", # Placeholder
    "Aston Martin": "Aston Martin",
    "Ferrari": "Ferrari",
    "McLaren": "McLaren",
    "Mercedes": "Mercedes",
    "Alpine": "Alpine",
    "Williams": "Williams"
}

def safe_int(val, default=0):
    """Safely converts a value to int, handling floats, strings, and NaNs."""
    try:
        if pd.isna(val) or str(val).strip() == '':
            return default
        return int(float(val))
    except:
        return default

def check_finished(status):
    """Returns True if the driver actually crossed the finish line."""
    s = str(status).lower()
    return s == 'finished' or s.startswith('+')

def calculate_race_scores(df, year, round_name, race_payouts=None, is_test=False):
    """
    Calculates scores for a given race and updates the DataFrame.
    Returns: (updated_df, log_message)
    """
    try:
        # 1. Get Race Data
        if is_test:
            # Pick a random race from previous year for testing
            test_year = year - 1
            schedule = fastf1.get_event_schedule(test_year, include_testing=False)
            rounds = schedule['RoundNumber'].unique().tolist()
            random_round = random.choice(rounds) if rounds else 1
            
            session = fastf1.get_session(test_year, random_round, 'R')
            session.load(telemetry=False, weather=False)
            round_name = f"TEST: {session.event['EventName']} {test_year}"
        else:
            session = fastf1.get_session(year, round_name, 'R')
            session.load(telemetry=False, weather=False)
            
        results = session.results
        
        if results.empty:
            return df, f"No results available for {round_name}."

        try:
            fastest_lap_driver = session.laps.pick_fastest()['Driver']
        except:
            fastest_lap_driver = None

        # 2. Prepare DataFrame
        if df.empty:
            return df, "No players found in the league data."

        # Ensure numeric columns
        cols = ['Current Score', 'Total Winnings', 'Previous Pos', 'Last Race Pts', 'Total Spent']
        for c in cols:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
            else:
                df[c] = 0

        # Snapshot Previous Positions (based on score BEFORE this race)
        df['Previous Pos'] = df['Current Score'].rank(ascending=False, method='min').fillna(0).astype(int)

        points_map = {1:25, 2:18, 3:15, 4:12, 5:10, 6:8, 7:6, 8:4, 9:2, 10:1}
        race_points_this_weekend = [] 

        # 3. Process Each Player
        for index, row in df.iterrows():
            try:
                # Handle smart quotes and parsing
                raw_picks = str(row['Picks']).replace('“', '"').replace('”', '"').replace("‘", "'").replace("’", "'")
                player_picks = ast.literal_eval(raw_picks)
            except:
                race_points_this_weekend.append(0)
                continue
                
            this_race_total = 0
            
            for pick in player_picks:
                # --- DRIVER SCORING ---
                if pick in DRIVER_MAP:
                    abbr = DRIVER_MAP[pick]
                    d_data = results[results['Abbreviation'] == abbr]
                    if not d_data.empty:
                        d = d_data.iloc[0]
                        
                        # Safely parse positions
                        grid = safe_int(d.get('GridPosition'), 0)
                        
                        # Handle DNS (Did Not Start)
                        status = str(d['Status'])
                        if status == 'Did not start':
                            continue # No points for the weekend

                        # Handle Pit Lane Starts (Grid=0) -> 1 point (Pos 20)
                        if grid == 0:
                            grid = 20

                        # Scoring Logic
                        this_race_total += (21 - grid) # Grid Pts
                        
                        # Handle Disqualification (DSQ)
                        if 'Disqualified' in status or 'Excluded' in status:
                            this_race_total -= 20
                            continue # Grid points stand, -20 deduction, no other points
                        
                        # Lap Points (with fallback)
                        laps = safe_int(d.get('Laps'), 0)
                        if laps == 0:
                            try:
                                dlaps = session.laps.pick_driver(abbr)
                                if len(dlaps) > 0: laps = len(dlaps)
                            except: pass
                        this_race_total += laps
                        
                        if check_finished(status):
                            finish = safe_int(d.get('ClassifiedPosition'), 20)
                            gain = grid - finish
                            if gain > 0: this_race_total += gain # Improvement
                            this_race_total += points_map.get(finish, 0)
                        
                        if abbr == fastest_lap_driver:
                            this_race_total += 25

                # --- CONSTRUCTOR SCORING ---
                else:
                    # Map the pick to the official FastF1 name, or use the pick itself if not found
                    official_team_name = CONSTRUCTOR_MAP.get(pick, pick)
                    t_data = results[results['TeamName'] == official_team_name]
                    if not t_data.empty:
                        # 1. DSQ Deduction
                        dq_cars = t_data[t_data['Status'].str.contains("Disqualified|Excluded", na=False)]
                        this_race_total -= (len(dq_cars) * 10)

                        # Filter for ACTUAL finishers
                        finishers = []
                        for _, car in t_data.iterrows():
                            if check_finished(car['Status']):
                                finishers.append(car)
                        
                        # 2. Finishing Car Bonus
                        this_race_total += (len(finishers) * 10)
                        
                        # 3. Best Position Points
                        if finishers:
                            best_pos = 999
                            for car in finishers:
                                p = safe_int(car.get('ClassifiedPosition'), 999)
                                if p < best_pos: best_pos = p
                            this_race_total += points_map.get(best_pos, 0)
            
            race_points_this_weekend.append(this_race_total)

        # 4. Update DataFrame
        df['Last Race Pts'] = race_points_this_weekend
        df['Current Score'] = df['Current Score'] + race_points_this_weekend
        
        # Apply Payouts
        if race_payouts:
            # Rank based on this weekend only
            df['Weekend_Rank'] = df['Last Race Pts'].rank(ascending=False, method='min').astype(int)
            
            for i, p_amount in enumerate(race_payouts):
                target_rank = i + 1
                # Add winnings to anyone with this rank
                mask = df['Weekend_Rank'] == target_rank
                if mask.any():
                    df.loc[mask, 'Total Winnings'] += float(p_amount)

            df = df.drop(columns=['Weekend_Rank'])

        # Update Total Spent
        df['Total Spent'] += 5.0

        # Update Season Rank
        df['Pos'] = df['Current Score'].rank(ascending=False, method='min').fillna(0).astype(int)

        # Sort
        df = df.sort_values(by=['Current Score', 'Total Winnings'], ascending=False)
        
        return df, f"Successfully synced {round_name}!"

    except Exception as e:
        return df, f"Error during sync: {str(e)}"