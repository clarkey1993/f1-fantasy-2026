import streamlit as st
import pandas as pd
import ast
import datetime

# --- CONFIGURATION FOR VISUALS ---
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
    "Audi": {"color": "#52E252", "slug": "kick-sauber"}, # Using Sauber assets for Audi placeholder
    "Cadillac": {"color": "#FFD700", "slug": "f1"}, # Generic placeholder
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

def get_team_info(name, is_constructor=False):
    if is_constructor:
        team_name = name
    else:
        team_name = DRIVER_TEAM_MAP.get(name, "Cadillac")
    
    # Handle edge cases or missing teams (partial match)
    if team_name not in TEAM_CONFIG:
        for t in TEAM_CONFIG:
            if t in team_name:
                team_name = t
                break
        else:
            team_name = "Cadillac" # Fallback
            
    return team_name, TEAM_CONFIG.get(team_name, TEAM_CONFIG["Cadillac"])

def render_card(name, is_constructor=False):
    team_name, config = get_team_info(name, is_constructor)
    color = config['color']
    slug = config['slug']
    
    # Construct Image URLs (Using standard F1 web assets)
    logo_url = f"https://media.formula1.com/content/dam/fom-website/teams/2024/{slug}-logo.png.transform/2col/image.png"
    car_url = f"https://media.formula1.com/d_team_car_fallback_image.png/content/dam/fom-website/teams/2024/{slug}.png.transform/4col/image.png"
    
    html = f"""
    <div style="background-color: {color}; padding: 10px; border-radius: 10px; margin-bottom: 10px; display: flex; align-items: center; justify-content: space-between; box-shadow: 0 4px 6px rgba(0,0,0,0.2); color: white; overflow: hidden; height: 70px;">
        <div style="display: flex; align-items: center; gap: 10px; z-index: 2;">
            <img src="{logo_url}" style="width: 35px; height: 35px; object-fit: contain; background: rgba(255,255,255,0.2); border-radius: 50%; padding: 3px;">
            <div style="line-height: 1.2;">
                <div style="font-weight: 800; font-size: 15px; text-shadow: 0 1px 2px rgba(0,0,0,0.6);">{name}</div>
                <div style="font-size: 11px; opacity: 0.95; text-shadow: 0 1px 2px rgba(0,0,0,0.6);">{team_name}</div>
            </div>
        </div>
        <img src="{car_url}" style="height: 55px; object-fit: contain; transform: scale(1.3) translateX(10px);">
    </div>
    """
    return html

def show_dashboard(conn, url):
    # Initialize session state for user login
    if 'user_nick' not in st.session_state:
        st.session_state.user_nick = None
    if 'is_admin' not in st.session_state:
        st.session_state.is_admin = False

    # --- NOT LOGGED IN: SHOW LOGIN FORM ---
    if st.session_state.user_nick is None:
        st.header("👤 Player Login")
        st.caption("Access your private dashboard to see your team and stats.")
        
        with st.form("login_form"):
            user = st.text_input("Email Address")
            pw = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Log In")
            
            if submitted:
                # 1. Check for Admin Login
                try:
                    admin_pw = st.secrets.get("admin_password", "admin12345")
                except Exception:
                    admin_pw = "admin12345"

                if user.strip().lower() == "admin" and pw == admin_pw:
                    st.session_state.user_nick = "Admin"
                    st.session_state.is_admin = True
                    st.rerun()

                try:
                    df = conn.read(spreadsheet=url, ttl=0)
                    
                    if 'Password' not in df.columns:
                        st.error("System Error: Password column missing in database. Please ask Admin to reset the sheet.")
                    else:
                        # Find user (case-insensitive search)
                        user_row = df[df['Email'].astype(str).str.strip().str.lower() == user.strip().lower()]
                        
                        if not user_row.empty:
                            stored_pw = str(user_row.iloc[0]['Password'])
                            if stored_pw == pw:
                                st.session_state.user_nick = user_row.iloc[0]['Nickname']
                                st.rerun()
                            else:
                                st.error("❌ Incorrect Password.")
                        else:
                            st.error("❌ User not found.")
                except Exception as e:
                    st.error(f"Login Error: {e}")
    
    # --- LOGGED IN: SHOW DASHBOARD ---
    else:
        # Special View for Admin
        if st.session_state.is_admin:
            st.title("🔐 Commissioner Access")
            st.success("You are logged in as Admin.")
            st.info("Navigate to the '🛠️ Admin' tab to manage the league.")
            if st.button("Log Out"):
                st.session_state.user_nick = None
                st.session_state.is_admin = False
                st.rerun()
            return

        try:
            # Fetch fresh data for the logged-in user
            df = conn.read(spreadsheet=url, ttl=0)
            user_row = df[df['Nickname'] == st.session_state.user_nick].iloc[0]
            
            c_head, c_btn = st.columns([4, 1])
            with c_head:
                st.title(f"Welcome, {user_row['Name']}!")
            with c_btn:
                if st.button("Log Out"):
                    st.session_state.user_nick = None
                    st.rerun()
            
            st.divider()
            
            # --- ENHANCED STATS DASHBOARD ---
            st.subheader("📊 Season Performance")
            
            # Calculate Deltas and Financials
            pos = int(user_row['Pos']) if pd.notna(user_row['Pos']) else 0
            prev_pos = int(user_row['Previous Pos']) if 'Previous Pos' in user_row and pd.notna(user_row['Previous Pos']) else 0
            rank_delta = prev_pos - pos if prev_pos > 0 else 0
            
            current_score = int(user_row['Current Score']) if pd.notna(user_row['Current Score']) else 0
            last_race_pts = int(user_row['Last Race Pts']) if 'Last Race Pts' in user_row and pd.notna(user_row['Last Race Pts']) else 0
            
            total_spent = float(user_row.get('Total Spent', 0))
            total_winnings = float(user_row['Total Winnings']) if pd.notna(user_row['Total Winnings']) else 0.0
            net_profit = total_winnings - total_spent

            # Display Metrics with Deltas
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("🏆 League Rank", f"#{pos}", delta=rank_delta, delta_color="normal")
            m2.metric("🏁 Total Points", current_score, delta=f"+{last_race_pts} last race")
            m3.metric("💸 Net Profit", f"£/€{net_profit:.2f}", delta=None)
            m4.metric("💰 Total Winnings", f"£/€{total_winnings:.2f}")
            
            st.divider()

            # --- VISUAL TEAM GARAGE ---
            current_year = datetime.datetime.now().year
            st.subheader(f"🏎️ Your {current_year} Garage")
            if pd.notna(user_row['Picks']):
                raw_picks = str(user_row['Picks']).strip().replace('“', '"').replace('”', '"').replace("‘", "'").replace("’", "'")
                picks = ast.literal_eval(raw_picks)
                
                drivers = picks[:10]
                constructors = picks[10:]
                
                col_d, col_c = st.columns(2)
                
                with col_d:
                    st.markdown("### 🧑‍✈️ Drivers")
                    # Split drivers into two sub-columns for a grid look
                    d1, d2 = st.columns(2)
                    for i, d in enumerate(drivers):
                        if i % 2 == 0:
                            d1.markdown(render_card(d, is_constructor=False), unsafe_allow_html=True)
                        else:
                            d2.markdown(render_card(d, is_constructor=False), unsafe_allow_html=True)
                            
                with col_c:
                    st.markdown("### 🛠️ Constructors")
                    # Split constructors into two sub-columns
                    c1, c2 = st.columns(2)
                    for i, c in enumerate(constructors):
                        if i % 2 == 0:
                            c1.markdown(render_card(c, is_constructor=True), unsafe_allow_html=True)
                        else:
                            c2.markdown(render_card(c, is_constructor=True), unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Error loading dashboard: {e}")