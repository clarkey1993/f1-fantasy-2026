import fastf1
import pandas as pd
import os
from streamlit_gsheets import GSheetsConnection

# Cache setup for fast loading
if not os.path.exists('f1_cache'):
    os.makedirs('f1_cache')
fastf1.Cache.enable_cache('f1_cache') 

# Mapping for the scoring engine to understand your form data
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

def run_sync(conn, url, year, round_name):
    """The main function called by your Admin button"""
    try:
        # 1. Get Race Data from FastF1
        session = fastf1.get_session(year, round_name, 'R')
        session.load(telemetry=False, weather=False)
        results = session.results
        
        if results.empty:
            return "No results available yet for this race."

        # 2. Pull your League Data from Google Sheets
        df = conn.read(spreadsheet=url, ttl=0)
        if df.empty:
            return "No players found in the sheet."

        # 3. Calculate points for every player
        points_map = {1:25, 2:18, 3:15, 4:12, 5:10, 6:8, 7:6, 8:4, 9:2, 10:1}
        
        # We'll store the new points in a list to add them later
        new_scores = []
        
        for index, row in df.iterrows():
            player_picks = eval(row['Picks']) # Converts the string "[...]" back to a list
            race_points = 0
            
            # Separate drivers and teams from the picks list
            # (Adjust logic based on how you saved them in tab1)
            for pick in player_picks:
                # Is it a Driver?
                if pick in DRIVER_MAP:
                    abbr = DRIVER_MAP[pick]
                    d_data = results[results['Abbreviation'] == abbr]
                    if not d_data.empty:
                        # Grid Points + Laps + Gains + Finishing Pos
                        race_points += (21 - int(d_data['GridPosition'].iloc[0]))
                        race_points += int(d_data['Laps'].iloc[0])
                        gain = int(d_data['GridPosition'].iloc[0]) - int(d_data['ClassifiedPosition'].iloc[0])
                        if gain > 0: race_points += gain
                        race_points += points_map.get(int(d_data['ClassifiedPosition'].iloc[0]), 0)
                
                # Is it a Team?
                else:
                    t_data = results[results['TeamName'] == pick]
                    if not t_data.empty:
                        finishing_cars = t_data[t_data['Status'] == 'Finished']
                        race_points += (len(finishing_cars) * 10)
                        best_pos = t_data['ClassifiedPosition'].min()
                        race_points += points_map.get(int(best_pos), 0)
            
            # IMPORTANT: CUMULATIVE ADDITION
            # Add the new race points to whatever they already had
            current_total = pd.to_numeric(row['Current Score'], errors='coerce') or 0
            new_scores.append(current_total + race_points)

        # 4. Update the Dataframe and Push to Cloud
        df['Current Score'] = new_scores
        
        # Sort by score to update positions
        df = df.sort_values(by='Current Score', ascending=False)
        df['Pos'] = range(1, len(df) + 1)
        
        conn.update(spreadsheet=url, data=df)
        return f"Successfully synced {round_name}! Standings updated."

    except Exception as e:
        return f"Error during sync: {str(e)}"

    except Exception as e:
        # If the race hasn't happened, return 0 instead of crashing
        print(f"Data not available yet for {round_name} {year}")
        return 0

# Return a dictionary so we can handle tie-breakers later
    return {
        "total": total_score,
        "driver_only": driver_score_sum, # Tie-breaker 1 & 2
        "best_driver": max_individual_driver_score # Tie-breaker 3
    }
# --- QUICK TEST ---
# Let's pretend it's the end of the race and we check a team
if __name__ == "__main__":
    print("Fetching results and calculating points...")
    # Using 2024 results as a test since 2026 hasn't happened yet!
    test_score = calculate_points(2024, 'Bahrain', ['VER', 'PER', 'SAI'])
    print(f"Test Score for VER, PER, SAI in Bahrain 2024: {test_score} points")