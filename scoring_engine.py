import fastf1
import pandas as pd
import os  # <--- Add this line

# --- NEW: Create the cache folder if it doesn't exist ---
if not os.path.exists('f1_cache'):
    os.makedirs('f1_cache')

# Enable caching so it doesn't download the same data twice
fastf1.Cache.enable_cache('f1_cache') 

def calculate_points(year, round_name, driver_picks, team_picks):
    try:
        session = fastf1.get_session(year, round_name, 'R')
        session.load(telemetry=False, weather=False)
        
        # Check if results are actually available
        if session.results.empty:
            return 0
            
        results = session.results
        
        # Try to get fastest lap, but don't crash if it's missing
        try:
            fastest_lap_driver = session.laps.pick_fastest()['Driver']
        except:
            fastest_lap_driver = None
            
        total_score = 0
        points_map = {1:25, 2:18, 3:15, 4:12, 5:10, 6:8, 7:6, 8:4, 9:2, 10:1}

        # --- DRIVER SCORING ---
        for driver in driver_picks:
            d_data = results[results['Abbreviation'] == driver]
            if not d_data.empty:
                # 1. Grid Points
                total_score += (21 - int(d_data['GridPosition'].iloc[0]))
                # 2. Laps Completed
                total_score += int(d_data['Laps'].iloc[0])
                # 3. Improvement Bonus
                gain = int(d_data['GridPosition'].iloc[0]) - int(d_data['ClassifiedPosition'].iloc[0])
                if gain > 0: total_score += gain
                # 4. Finishing Position
                total_score += points_map.get(int(d_data['ClassifiedPosition'].iloc[0]), 0)
                # 5. Fastest Lap (25 pts)
                if driver == fastest_lap_driver:
                    total_score += 25

        # --- CONSTRUCTOR SCORING ---
        for team in team_picks:
            team_cars = results[results['TeamName'] == team]
            finishing_cars = team_cars[team_cars['Status'] == 'Finished']
            total_score += (len(finishing_cars) * 10)
            if not team_cars.empty:
                best_pos = team_cars['ClassifiedPosition'].min()
                total_score += points_map.get(int(best_pos), 0)

        return total_score

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