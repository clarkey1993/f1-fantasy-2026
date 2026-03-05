import streamlit as st
import pandas as pd
import os
import datetime
import scoring_engine
from streamlit_gsheets import GSheetsConnection

# 1. SETUP & CONNECTION
st.set_page_config(page_title="F1 Fantasy 2026", layout="wide")

# Google Sheet URL
url = "https://docs.google.com/spreadsheets/d/150YSDU3o1SiEM1WHpPEK9pNPnGUu03qxR26H77RnApw/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. SAVE FUNCTION
def save_to_gsheet(new_row_dict):
    try:
        # Pull the current data from the sheet
        existing_df = conn.read(spreadsheet=url, ttl=0)
        
        # Create a DataFrame for the new signup
        new_entry_df = pd.DataFrame([new_row_dict])
        
        # Combine and push back to Google Sheets
        updated_df = pd.concat([existing_df, new_entry_df], ignore_index=True)
        conn.update(spreadsheet=url, data=updated_df)
        return True
    except Exception as e:
        st.error(f"❌ Error saving to Google Sheets: {e}")
        return False

# 3. UI LAYOUT
st.title("🏁 F1 Fantasy Championship 2026")

tab1, tab2, tab3 = st.tabs(["📜 Rules & Signup", "📊 Leaderboard", "🛠️ Admin"])

# --- TAB 1: SIGNUP ---
with tab1:
    st.header("📜 Rules & Signup")

    with st.expander("📜 View 2026 Fantasy League Rules"):
        st.write("""
        ### How to Score Points:
        * **Qualifying:** 21 points minus your Grid Position.
        * **Race Completion:** 1 point for every lap finished.
        * **Overtaking:** 1 point for every position gained.
        * **Finishing:** Standard FIA points (25, 18, 15...).
        * **Constructors:** Points based on team performance.
        
        **Deadline:** Entries must be submitted before Qualifying on Saturday!
        """)

    with st.form("signup_form", clear_on_submit=True):
        st.subheader("2026 Season Selections")
        name = st.text_input("Full Name")
        nickname = st.text_input("Team Nickname (e.g. 'The Silver Arrows')")
        email = st.text_input("Email")
        
        col1, col2 = st.columns(2)
        with col1:
            g_a = st.multiselect("GROUP A (Pick 2)", ["Charles Leclerc", "George Russell", "Lando Norris", "Max Verstappen"], max_selections=2)
            g_b = st.multiselect("GROUP B (Pick 2)", ["Fernando Alonso", "Kimi Antonelli", "Lewis Hamilton", "Oscar Piastri"], max_selections=2)
            g_c = st.selectbox("GROUP C (Pick 1)", ["Carlos Sainz Jnr", "Isack Hadjar", "Pierre Gasly"], index=None, placeholder="Choose a driver...")
            g_d = st.selectbox("GROUP D (Pick 1)", ["Alex Albon", "Lance Stroll"], index=None, placeholder="Choose a driver...")
            g_e = st.selectbox("GROUP E (Pick 1)", ["Esteban Ocon", "Liam Lawson", "Oliver Bearman"], index=None, placeholder="Choose a driver...")
            g_f = st.selectbox("GROUP F (Pick 1)", ["Arvid Lindblad", "Nico Hulkenberg"], index=None, placeholder="Choose a driver...")
            g_g = st.selectbox("GROUP G (Pick 1)", ["Franco Colapinto", "Gabriel Bortoleto"], index=None, placeholder="Choose a driver...")
            g_h = st.selectbox("GROUP H (Pick 1)", ["Sergio Perez", "Valtteri Bottas"], index=None, placeholder="Choose a driver...")

        with col2:
            g_i = st.multiselect("GROUP I (Pick 2)", ["Ferrari", "McLaren", "Mercedes"], max_selections=2)
            g_j = st.selectbox("GROUP J (Pick 1)", ["Aston Martin", "Red Bull"], index=None, placeholder="Choose a team...")
            g_k = st.selectbox("GROUP K (Pick 1)", ["Alpine", "Williams"], index=None, placeholder="Choose a team...")
            g_l = st.selectbox("GROUP L (Pick 1)", ["Audi", "Haas"], index=None, placeholder="Choose a team...")
            g_m = st.selectbox("GROUP M (Pick 1)", ["Cadillac", "Racing Bulls"], index=None, placeholder="Choose a team...")

        rules_check = st.checkbox("I agree to the rules and the £5 per race entry fee.")
        
        if st.form_submit_button("Submit Team"):
            required_selections = [g_c, g_d, g_e, g_f, g_g, g_h, g_j, g_k, g_l, g_m]
            
            if not rules_check:
                st.error("You must agree to the rules to join.")
            elif None in required_selections or not name or not nickname:
                st.error("Please fill in all fields and make a selection in every group.")
            elif len(g_a) != 2 or len(g_b) != 2 or len(g_i) != 2:
                st.error("Please ensure you have selected exactly TWO choices for Groups A, B, and I.")
            else:
                # Combine all picks into one string/list for the database
                all_picks = g_a + g_b + [g_c, g_d, g_e, g_f, g_g, g_h] + g_i + [g_j, g_k, g_l, g_m]
                
                # Construct the final dictionary
                new_entry_data = {
                    "Name": name,
                    "Nickname": nickname,
                    "Email": email,
                    "Picks": str(all_picks),
                    "Current Score": 0,
                    "Pos": 0,
                    "Previous Pos": 0
                }
                
                # Save it
                if save_to_gsheet(new_entry_data):
                    st.success(f"✅ Registration successful! Good luck, {name}!")

# --- TAB 2: LEADERBOARD ---
with tab2:
    st.header("🏆 2026 League Standings")
    try:
        df_leaderboard = conn.read(spreadsheet=url, ttl=0)
        if not df_leaderboard.empty:
            df_leaderboard['Pos'] = pd.to_numeric(df_leaderboard['Pos']).fillna(0).astype(int)
            df_leaderboard['Current Score'] = pd.to_numeric(df_leaderboard['Current Score']).fillna(0).astype(int)
            mod_time = datetime.datetime.now().strftime('%d %b %Y, %H:%M')
            desired_cols = ['Pos', 'Nickname', 'Name', 'Current Score']
            available_cols = [c for c in desired_cols if c in df_leaderboard.columns]
            
            st.table(df_leaderboard[available_cols if available_cols else df_leaderboard.columns])
            st.caption(f"🕒 Last Updated: {mod_time}")
        else:
            st.info("No entries yet. Be the first to join!")
    except Exception:
        st.info("The leaderboard is currently empty.")

# --- TAB 3: ADMIN ---
with tab3:
    st.subheader("🔐 Commissioner Access")
    admin_pw = st.text_input("Enter Admin Password", type="password", key="admin_login")
    
    if admin_pw == "admin12345":
        st.success("Welcome back, Commissioner!")
        st.divider()
        
        col1, col2 = st.columns(2)
        with col1:
            st.write("### 🏁 Race Operations")
            if st.button("🔄 Sync Latest Results"):
                with st.spinner("Fetching FastF1 data and updating scores..."):
                    # Call the function from your scoring_engine.py
                    #result_msg = scoring_engine.run_sync(conn, url, 2026, 'Australia')
                    result_msg = scoring_engine.run_sync(conn, url, 2025, 'Abu Dhabi')
                    
                    if "Successfully" in result_msg:
                        st.balloons()
                        st.success(result_msg)
                        st.rerun()
                    else:
                        st.error(result_msg)

        with col2:
            st.write("### ⚠️ Danger Zone")
            if st.button("🗑️ RESET LEAGUE (Wipe Sheet)"):
                # This clears the sheet and leaves only the headers
                empty_df = pd.DataFrame(columns=['Name', 'Nickname', 'Email', 'Picks', 'Current Score', 'Pos', 'Previous Pos'])
                conn.update(spreadsheet=url, data=empty_df)
                st.warning("Cloud data wiped. Starting fresh!")
                st.rerun()
                
    elif admin_pw != "":

        st.error("Incorrect Password.")
