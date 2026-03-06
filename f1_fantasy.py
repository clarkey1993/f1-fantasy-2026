import streamlit as st
import pandas as pd
import datetime
from streamlit_gsheets import GSheetsConnection

# Import your custom modules
from modules import leaderboard, signup, admin, ui_styles

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

tab1, tab2, tab3 = st.tabs(["📊 Leaderboard", "✍️ Rules & Signup", "🛠️ Admin"])

# --- TAB 1: LEADERBOARD ---
with tab1:
    leaderboard.show_leaderboard(conn, url)

# --- TAB 2: SIGNUP ---
with tab2:
    signup.show_signup_form(conn, url, save_to_gsheet)

# --- TAB 3: ADMIN ---
with tab3:
    admin.show_admin_panel(conn, url)
