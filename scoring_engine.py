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
    "Audi": "Kick Sauber", # Placeholder
    "Cadillac": "Williams", # Placeholder
    "Aston Martin": "Aston Martin",
    "Ferrari": "Ferrari",
    "McLaren": "McLaren",
    "Mercedes": "Mercedes",
    "Alpine": "Alpine",
    "Williams": "Williams"
}

def check_finished(status):
    """Returns True if the driver actually crossed the finish line."""
    s = str(status).lower()
    return s == 'finished' or s.startswith('+')

def safe_int(val, default=0):
    """Safely converts a value to int, handling floats, strings, and NaNs."""
    try:
        if pd.isna(val) or str(val).strip() == '':
            return default
        return int(float(val))
    except:
        return default

def run_sync(conn, url, year, round_name, race_payouts=None, is_test=False):
    try:
        # 1. Get Race Data
        if is_test:
            # Pick a random race from 2024 (last complete season)
            test_year = year - 1
            schedule = fastf1.get_event_schedule(test_year, include_testing=False)
            rounds = schedule['RoundNumber'].unique().tolist()
            random_round = random.choice(rounds)
            
            session = fastf1.get_session(test_year, random_round, 'R')
            session.load(telemetry=False, weather=False)
            round_name = f"TEST: {session.event['EventName']} {test_year}"
        else:
            session = fastf1.get_session(year, round_name, 'R')
            session.load(telemetry=False, weather=False)
            
        results = session.results
        
        if results.empty:
            return f"No results available for {round_name}."

        try:
            fastest_lap_driver = session.laps.pick_fastest()['Driver']
        except:
            fastest_lap_driver = None

        # 2. Pull League Data
        df = conn.read(spreadsheet=url, ttl=0)
        if df.empty:
            return "No players found in the sheet."

        # --- SNAPSHOT PREVIOUS POSITIONS ---
        # Ensure numeric and calculate rank based on score BEFORE adding new points
        df['Current Score'] = pd.to_numeric(df['Current Score'], errors='coerce').fillna(0)
        df['Previous Pos'] = df['Current Score'].rank(ascending=False, method='min').fillna(0).astype(int)

        points_map = {1:25, 2:18, 3:15, 4:12, 5:10, 6:8, 7:6, 8:4, 9:2, 10:1}
        race_points_this_weekend = [] 

        # 3. Process Each Player based on 29th Year Rules
        for index, row in df.iterrows():
            try:
                player_picks = ast.literal_eval(row['Picks'])
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
                        
                        # 1. GRID POINTS (20 for 1st ... 1 for 20th)
                        grid = safe_int(d.get('GridPosition'), 0)
                        
                        # Handle DNS (Did Not Start)
                        status = str(d['Status'])
                        if status == 'Did not start':
                            continue # No points for the weekend

                        # Handle Pit Lane Starts (Grid=0) -> 1 point (Pos 20)
                        if grid == 0:
                            grid = 20
                        
                        # Add Grid Points
                        this_race_total += (21 - grid)

                        # Handle Disqualification (DSQ)
                        if 'Disqualified' in status or 'Excluded' in status:
                            this_race_total -= 20
                            continue # Grid points stand, -20 deduction, no other points

                        # 2. LAP POINTS (1 pt per lap)
                        laps = safe_int(d.get('Laps'), 0)
                        
                        # Fallback: If laps is 0, try counting from session timing data
                        if laps == 0:
                            try:
                                dlaps = session.laps.pick_driver(abbr)
                                if len(dlaps) > 0:
                                    laps = len(dlaps)
                            except:
                                pass
                                
                        this_race_total += laps
                        
                        # 3. FINISHING POINTS (Only if actually finished)
                        finish = 20 # Default
                        if check_finished(status):
                            finish = safe_int(d.get('ClassifiedPosition'), 20)

                            # Improvement Bonus
                            gain = grid - finish
                            if gain > 0: this_race_total += gain # Improvement
                            
                            # Top 10 Finishing Points
                            this_race_total += points_map.get(finish, 0)
                        
                        # 4. FASTEST LAP (25 pts)
                        if abbr == fastest_lap_driver:
                            this_race_total += 25
                        
                        # Debug print to help verify points
                        # print(f"  {pick}: Grid={grid}, Laps={laps}, Finish={finish}, Status={status} -> Pts={this_race_total}")

                # --- CONSTRUCTOR SCORING ---
                else:
                    # Map to official team name
                    official_team = CONSTRUCTOR_MAP.get(pick, pick)
                    t_data = results[results['TeamName'] == official_team]
                    
                    if not t_data.empty:
                        # 1. DSQ Deduction (-10 per car)
                        dq_cars = t_data[t_data['Status'].str.contains("Disqualified|Excluded", na=False)]
                        this_race_total -= (len(dq_cars) * 10)

                        # Filter for ACTUAL finishers (passed chequered flag)
                        finishers = []
                        for _, car in t_data.iterrows():
                            if check_finished(car['Status']):
                                finishers.append(car)
                        
                        # 2. Finishing Car Bonus (10 pts per car)
                        this_race_total += (len(finishers) * 10)
                        
                        # 3. Best Position Points (Highest placed car only)
                        if finishers:
                            best_pos = 999
                            for car in finishers:
                                p = safe_int(car.get('ClassifiedPosition'), 999)
                                if p < best_pos: best_pos = p
                            
                            this_race_total += points_map.get(best_pos, 0)
            
            race_points_this_weekend.append(this_race_total)

        # 4. Apply Logic to DataFrame
        # Store THIS weekend's points separately for the Recap table
        df['Last Race Pts'] = race_points_this_weekend
        
        # Add this weekend's points to the total season score
        df['Current Score'] = df['Current Score'] + race_points_this_weekend
        
        # Apply Payouts
        if race_payouts:
            # Rank players based JUST on this weekend's performance
            # Ties handled by 'min' (e.g. two people tie for 1st, both get 1st prize)
            df['Weekend_Rank'] = df['Last Race Pts'].rank(ascending=False, method='min').astype(int)
            
            if 'Total Winnings' not in df.columns:
                df['Total Winnings'] = 0.0
            
            df['Total Winnings'] = pd.to_numeric(df['Total Winnings']).fillna(0.0)
            
            # Map prizes: 1st place gets race_payouts[0], etc.
            for i, p_amount in enumerate(race_payouts):
                target_rank = i + 1
                df.loc[df['Weekend_Rank'] == target_rank, 'Total Winnings'] += float(p_amount)

        # Update Total Spent (Entry Fee per race)
        if 'Total Spent' not in df.columns:
            df['Total Spent'] = 0.0
        df['Total Spent'] = pd.to_numeric(df['Total Spent']).fillna(0.0)
        df['Total Spent'] += 5.0 # Cost per race

        # 5. Final Cleanup
        if 'Weekend_Rank' in df.columns:
            df = df.drop(columns=['Weekend_Rank'])

        # Update Season Rank (Pos) for the dashboard
        df['Pos'] = df['Current Score'].rank(ascending=False, method='min').fillna(0).astype(int)

        # Keep current order by Season Total for the save
        df = df.sort_values(by=['Current Score', 'Total Winnings'], ascending=False)
        
        # Save back to Google Sheets
        conn.update(spreadsheet=url, data=df)
        return f"Successfully synced {round_name}! Points and Payouts updated."

    except Exception as e:
        return f"Error during sync: {str(e)}"