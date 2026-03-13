"""
Shared F1 fantasy configuration - single source of truth for app.py and scoring.py.
"""

# App display names -> FastF1 three-letter abbreviation
DRIVER_MAP = {
    "Charles Leclerc": "LEC", "George Russell": "RUS", "Lando Norris": "NOR",
    "Max Verstappen": "VER", "Fernando Alonso": "ALO", "Kimi Antonelli": "ANT",
    "Lewis Hamilton": "HAM", "Oscar Piastri": "PIA", "Carlos Sainz Jnr": "SAI",
    "Isack Hadjar": "HAD", "Pierre Gasly": "GAS", "Alex Albon": "ALB",
    "Lance Stroll": "STR", "Esteban Ocon": "OCO", "Liam Lawson": "LAW",
    "Oliver Bearman": "BEA", "Arvid Lindblad": "LIN", "Nico Hulkenberg": "HUL",
    "Franco Colapinto": "COL", "Gabriel Bortoleto": "BOR", "Sergio Perez": "PER",
    "Valtteri Bottas": "BOT", "Jack Doohan": "DOO", "Yuki Tsunoda": "TSU",
}

# Driver -> constructor (app display names)
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
    "Isack Hadjar": "Racing Bulls", "Arvid Lindblad": "Racing Bulls", "Yuki Tsunoda": "Racing Bulls",
}

# App constructor names -> FastF1 TeamName (used in session.results)
# Values must match FastF1 session.results['TeamName'] exactly (Australia 2025: Alpine, Aston Martin, Ferrari, Haas F1 Team, Kick Sauber, McLaren, Mercedes, Racing Bulls, Red Bull Racing, Williams)
CONSTRUCTOR_MAP = {
    "Red Bull": "Red Bull Racing",
    "Racing Bulls": "Racing Bulls",  # FastF1 2025 uses "Racing Bulls" (was "RB" for AlphaTauri)
    "Haas": "Haas F1 Team",
    "Audi": "Kick Sauber",
    "Cadillac": "Williams",   # Placeholder for 2024 data; 2026 may use "Cadillac"
    "Aston Martin": "Aston Martin",
    "Ferrari": "Ferrari",
    "McLaren": "McLaren",
    "Mercedes": "Mercedes",
    "Alpine": "Alpine",
    "Williams": "Williams",
}

# Team config for UI (color, slug for assets)
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

def get_team_config(team_name):
    """Fuzzy match team name to config. Returns Cadillac config as default."""
    config = TEAM_CONFIG.get("Cadillac")
    for key, val in TEAM_CONFIG.items():
        if key.lower() in str(team_name).lower():
            config = val
            break
    return config

def app_constructor_to_fastf1(team_name):
    """Map app constructor name to FastF1 TeamName. Handles fuzzy match for external sources."""
    for app_name, ff1_name in CONSTRUCTOR_MAP.items():
        if app_name.lower() in str(team_name).lower():
            return ff1_name
    return team_name
