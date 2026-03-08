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
current_year = datetime.datetime.now().year
st.set_page_config(page_title=f"F1 Fantasy {current_year}", layout="wide", initial_sidebar_state="collapsed")

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
# Initialize admin state if not present
if 'is_admin' not in st.session_state:
    st.session_state.is_admin = False

# Sidebar Navigation
with st.sidebar:
    # Make title clickable (Home Button)
    if st.button(f"🏎️ F1 Fantasy {current_year}", use_container_width=True):
        st.session_state.nav_selection = "📊 Leaderboard"
        st.rerun()

    st.markdown("---")
    st.markdown("### 🧭 Menu")

    nav_options = ["📊 Leaderboard", "👤 My Team", "📰 Latest News & Results", "🏎️ F1 Table", "✍️ Rules & Signup"]
    if st.session_state.is_admin:
        nav_options.append("🛠️ Admin")

    selection = st.radio("Go to", nav_options, label_visibility="collapsed", key="nav_selection")

# --- PAGE ROUTING ---
if selection == "📊 Leaderboard":
    leaderboard.show_leaderboard(conn, url)
elif selection == "👤 My Team":
    player_dashboard.show_dashboard(conn, url)
elif selection == "📰 Latest News & Results":
    news.show_news()
elif selection == "🏎️ F1 Table":
    f1_standings.show_f1_standings()
elif selection == "✍️ Rules & Signup":
    signup.show_signup_form(conn, url, save_to_gsheet)
elif selection == "🛠️ Admin":
    admin.show_admin_panel(conn, url)
