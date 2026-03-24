"""
Shared F1 fantasy configuration - single source of truth for app.py and scoring.py.
"""
import unicodedata

# Fantasy league season year - used for production race sync and UI display
LEAGUE_YEAR = 2026

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
# Values must match FastF1 session.results['TeamName'] exactly
# 2026: Alpine, Aston Martin, Audi, Cadillac, Ferrari, Haas F1 Team, McLaren, Mercedes, Racing Bulls, Red Bull Racing, Williams
CONSTRUCTOR_MAP = {
    "Red Bull": "Red Bull Racing",
    "Racing Bulls": "Racing Bulls",
    "Haas": "Haas F1 Team",
    "Audi": "Audi",
    "Cadillac": "Cadillac",
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
    """
    Map player constructor pick to FastF1 TeamName (session.results['TeamName']).
    Same resolution for leaderboard sync, debug breakdown, and signup flows:
    NFKC normalize + strip, exact case-insensitive match on CONSTRUCTOR_MAP keys,
    then longest-key-first substring match (reduces ambiguous partial matches).
    """
    if team_name is None:
        return ""
    s = unicodedata.normalize("NFKC", str(team_name)).strip()
    if not s:
        return s
    s_lower = s.lower()
    for app_name, ff1_name in CONSTRUCTOR_MAP.items():
        if app_name.lower() == s_lower:
            return ff1_name
    for app_name, ff1_name in sorted(CONSTRUCTOR_MAP.items(), key=lambda kv: -len(kv[0])):
        if app_name.lower() in s_lower:
            return ff1_name
    return s
