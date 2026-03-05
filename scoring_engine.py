import fastf1
import pandas as pd
import os
import ast

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
            results = pd.DataFrame({
                'Abbreviation': ['VER', 'NOR', 'LEC', 'PIA', 'HAM', 'RUS', 'SAI', 'ALO', 'ANT', 'HUL'],
                'TeamName': ['Red Bull', 'McLaren', 'Ferrari', 'McLaren', 'Ferrari', 'Mercedes', 'Williams', 'Aston Martin', 'Mercedes', 'Audi'],
                'GridPosition': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
                'ClassifiedPosition': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
                'Laps': [57] * 10,
                'Status': ['Finished'] * 10
            })
            fastest_lap_driver = "VER"
            round_name = "STRESS TEST"
        else:
            session = fastf1.get_session(year, round_name, 'R')
            session.load(telemetry=False, weather=False)
            results = session.results
            
            if results.empty:
                return "No results available yet for this race."

            try:
                fastest_lap_driver = session.laps.pick_fastest()['Driver']
            except:
                fastest_lap_driver = None

        # 2. Pull League Data
        df = conn.read(spreadsheet=url, ttl=0)
        if df.empty:
            return "No players found in the sheet."

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
                        this_race_total += (21 - int(d['GridPosition'])) # Grid Pts
                        this_race_total += int(d['Laps']) # Lap Pts
                        
                        gain = int(d['GridPosition']) - int(d['ClassifiedPosition'])
                        if gain > 0: this_race_total += gain # Improvement
                        
                        if d['Status'] == 'Finished':
                            this_race_total += points_map.get(int(d['ClassifiedPosition']), 0)
                        
                        if abbr == fastest_lap_driver:
                            this_race_total += 25
                            
                        if "Disqualified" in d['Status'] or "Excluded" in d['Status']:
                            this_race_total -= 20

                # --- CONSTRUCTOR SCORING ---
                else:
                    t_data = results[results['TeamName'] == pick]
                    if not t_data.empty:
                        finished_cars = t_data[t_data['Status'] == 'Finished']
                        this_race_total += (len(finished_cars) * 10)
                        
                        if not finished_cars.empty:
                            best_pos = finished_cars['ClassifiedPosition'].min()
                            this_race_total += points_map.get(int(best_pos), 0)
                        
                        dq_cars = t_data[t_data['Status'].str.contains("Disqualified|Excluded", na=False)]
                        this_race_total -= (len(dq_cars) * 10)
            
            race_points_this_weekend.append(this_race_total)

        # 4. Apply Logic to DataFrame
        # Store THIS weekend's points separately for the Recap table
        df['Last Race Pts'] = race_points_this_weekend
        
        # Add this weekend's points to the total season score
        df['Current Score'] = pd.to_numeric(df['Current Score']).fillna(0) + race_points_this_weekend
        
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