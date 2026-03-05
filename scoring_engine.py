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
    """
    is_test: If True, bypasses FastF1 API and uses mock data to test the sheet connection.
    race_payouts: A list of 5 values [1st, 2nd, 3rd, 4th, 5th] 
    """
    try:
        # 1. Get Race Data
        if is_test:
            # --- MOCK DATA FOR PRE-SEASON TESTING ---
            # Simulates a basic result where the top drivers finish in order
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
            # --- REAL LIVE DATA ---
            session = fastf1.get_session(year, round_name, 'R')
            session.load(telemetry=False, weather=False)
            results = session.results
            
            if results.empty:
                return "No results available yet for this race."

            # Rule 16: Fastest Lap = 25 points
            try:
                fastest_lap_driver = session.laps.pick_fastest()['Driver']
            except:
                fastest_lap_driver = None

        # 2. Pull League Data
        df = conn.read(spreadsheet=url, ttl=0)
        if df.empty:
            return "No players found in the sheet."

        points_map = {1:25, 2:18, 3:15, 4:12, 5:10, 6:8, 7:6, 8:4, 9:2, 10:1}
        race_points_earned_this_weekend = [] 

        # 3. Process Each Player based on 29th Year Rules
        for index, row in df.iterrows():
            # Handle potential empty picks or formatting issues
            try:
                player_picks = ast.literal_eval(row['Picks'])
            except:
                race_points_earned_this_weekend.append(0)
                continue
                
            this_race_total = 0
            
            for pick in player_picks:
                # --- DRIVER SCORING ---
                if pick in DRIVER_MAP:
                    abbr = DRIVER_MAP[pick]
                    d_data = results[results['Abbreviation'] == abbr]
                    if not d_data.empty:
                        d = d_data.iloc[0]
                        
                        # Rule 6: Grid Points (21 - GridPos)
                        this_race_total += (21 - int(d['GridPosition']))
                        
                        # Rule 7: 1 point for every lap completed
                        this_race_total += int(d['Laps'])
                        
                        # Rule 7: Improvement Bonus (1 pt per position gained)
                        gain = int(d['GridPosition']) - int(d['ClassifiedPosition'])
                        if gain > 0: this_race_total += gain
                        
                        # Rule 8 & 10: Finishing Points (ONLY if they took the Chequered Flag)
                        if d['Status'] == 'Finished':
                            this_race_total += points_map.get(int(d['ClassifiedPosition']), 0)
                        
                        # Rule 16: Fastest Lap (25 points)
                        if abbr == fastest_lap_driver:
                            this_race_total += 25
                            
                        # Rule 22: Disqualification (-20 points)
                        if "Disqualified" in d['Status'] or "Excluded" in d['Status']:
                            this_race_total -= 20

                # --- CONSTRUCTOR SCORING ---
                else:
                    t_data = results[results['TeamName'] == pick]
                    if not t_data.empty:
                        # Rule 11: 10 pts per car that takes chequered flag
                        finished_cars = t_data[t_data['Status'] == 'Finished']
                        this_race_total += (len(finished_cars) * 10)
                        
                        # Rule 12-14: Best finishing car points (ONLY if it finished)
                        if not finished_cars.empty:
                            best_pos = finished_cars['ClassifiedPosition'].min()
                            this_race_total += points_map.get(int(best_pos), 0)
                        
                        # Rule 23: Team DQ (-10 points per car)
                        dq_cars = t_data[t_data['Status'].str.contains("Disqualified|Excluded", na=False)]
                        this_race_total -= (len(dq_cars) * 10)
            
            race_points_earned_this_weekend.append(this_race_total)

        # 4. Apply Logic to the Main DataFrame
        df['Current Score'] = pd.to_numeric(df['Current Score']).fillna(0) + race_points_earned_this_weekend
        
        # Calculate Winnings for this specific race performance
        if race_payouts:
            payout_df = pd.DataFrame({'race_pts': race_points_earned_this_weekend}, index=df.index)
            payout_df = payout_df.sort_values(by='race_pts', ascending=False)
            
            if 'Total Winnings' not in df.columns:
                df['Total Winnings'] = 0.0
            
            df['Total Winnings'] = pd.to_numeric(df['Total Winnings']).fillna(0.0)
            
            for rank, p_amount in enumerate(race_payouts):
                if rank < len(payout_df):
                    winner_idx = payout_df.index[rank]
                    df.at[winner_idx, 'Total Winnings'] += float(p_amount)

        # Update Final League Rankings
        df = df.sort_values(by='Current Score', ascending=False)
        df['Pos'] = range(1, len(df) + 1)
        
        # Save back to Google Sheets
        conn.update(spreadsheet=url, data=df)
        return f"Successfully synced {round_name}! Points and Payouts updated."

    except Exception as e:
        return f"Error during sync: {str(e)}"