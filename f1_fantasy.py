import streamlit as st
import pandas as pd
import datetime
from streamlit_gsheets import GSheetsConnection

# Import your custom modules
from modules import leaderboard, signup, admin, ui_styles
import modules.news as news
import modules.f1_standings as f1_standings
import modules.player_dashboard as player_dashboard

# 1. SETUP & CONNECTION
st.set_page_config(page_title="F1 Fantasy 2026", layout="wide")

# Apply the theme (CSS is now handled inside ui_styles.py)
ui_styles.apply_custom_styles()

# Google Sheet URL
url = "https://docs.google.com/spreadsheets/d/150YSDU3o1SiEM1WHpPEK9pNPnGUu03qxR26H77RnApw/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. SAVE FUNCTION (Passed to the signup module)
def save_to_gsheet(new_row_dict):
    try:
        existing_df = conn.read(spreadsheet=url, ttl=0)
        new_entry_df = pd.DataFrame([new_row_dict])
        updated_df = pd.concat([existing_df, new_entry_df], ignore_index=True)
        conn.update(spreadsheet=url, data=updated_df)
        return True
    except Exception as e:
        st.error(f"❌ Error saving to Google Sheets: {e}")
        return False

# 3. UI LAYOUT
st.title("🏁 F1 Fantasy Championship 2026")

# Initialize admin state if not present
if 'is_admin' not in st.session_state:
    st.session_state.is_admin = False

# Dynamic Tabs: Only show Admin tab if logged in as Admin
tabs_list = ["📊 Leaderboard", " My Team", " Latest News", "🏎️ F1 Table", "✍️ Rules & Signup"]
if st.session_state.is_admin:
    tabs_list.append("🛠️ Admin")

tabs = st.tabs(tabs_list)

# --- TAB 1: LEADERBOARD ---
with tabs[0]:
    leaderboard.show_leaderboard(conn, url)

# --- TAB 2: MY TEAM (LOGIN) ---
with tabs[1]:
    player_dashboard.show_dashboard(conn, url)

# --- TAB 3: NEWS ---
with tabs[2]:
    news.show_news()

# --- TAB 4: F1 TABLE ---
with tabs[3]:
    f1_standings.show_f1_standings()

# --- TAB 5: SIGNUP ---
with tabs[4]:
    signup.show_signup_form(conn, url, save_to_gsheet)

# --- TAB 6: ADMIN ---
if st.session_state.is_admin and len(tabs) > 5:
    with tabs[5]:
        admin.show_admin_panel(conn, url)
