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

def run_sync(conn, url, year, round_name, race_payouts=None, is_test=False):
    try:
        # 1. Get Race Data
        if is_test:
            # Pick a random race from 2024 (last complete season)
            test_year = 2025
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
                        
                        # Safely parse positions
                        try:
                            grid = int(d['GridPosition'])
                        except:
                            grid = 20
                            
                        try:
                            finish = int(d['ClassifiedPosition'])
                            is_classified = True
                        except:
                            finish = 20
                            is_classified = False

                        this_race_total += (21 - grid) # Grid Pts
                        this_race_total += int(d['Laps']) # Lap Pts
                        
                        if is_classified:
                            gain = grid - finish
                            if gain > 0: this_race_total += gain # Improvement
                            this_race_total += points_map.get(finish, 0)
                        
                        if abbr == fastest_lap_driver:
                            this_race_total += 25
                            
                        if "Disqualified" in d['Status'] or "Excluded" in d['Status']:
                            this_race_total -= 20

                # --- CONSTRUCTOR SCORING ---
                else:
                    t_data = results[results['TeamName'] == pick]
                    if not t_data.empty:
                        # Filter for cars that have a numeric ClassifiedPosition (Finished or +1 Lap etc)
                        # We use pd.to_numeric with coerce to turn 'R' into NaN, then dropna
                        classified_cars = t_data.copy()
                        classified_cars['ClassifiedPosNumeric'] = pd.to_numeric(classified_cars['ClassifiedPosition'], errors='coerce')
                        finished_cars = classified_cars.dropna(subset=['ClassifiedPosNumeric'])
                        
                        this_race_total += (len(finished_cars) * 10)
                        
                        if not finished_cars.empty:
                            best_pos = int(finished_cars['ClassifiedPosNumeric'].min())
                            this_race_total += points_map.get(best_pos, 0)
                        
                        dq_cars = t_data[t_data['Status'].str.contains("Disqualified|Excluded", na=False)]
                        this_race_total -= (len(dq_cars) * 10)
            
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

        # Keep current order by Season Total for the save
        df = df.sort_values(by=['Current Score', 'Total Winnings'], ascending=False)
        
        # Save back to Google Sheets
        conn.update(spreadsheet=url, data=df)
        return f"Successfully synced {round_name}! Points and Payouts updated."

    except Exception as e:
        return f"Error during sync: {str(e)}"