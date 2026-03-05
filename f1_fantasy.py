import streamlit as st
import pandas as pd
import os
import datetime
import scoring_engine
from streamlit_gsheets import GSheetsConnection

# 1. SETUP & CONNECTION
st.set_page_config(page_title="F1 Fantasy 2026", layout="wide")

st.markdown("""
    <style>
        /* Target the main app background */
        .stApp {
            background-color: #0E1117;
        }
        /* Target the top header area */
        [data-testid="stHeader"] {
            background-color: rgba(0,0,0,0);
        }
        /* Target the main content area */
        .main {
            background-color: #0E1117;
        }
        /* Target the bottom area */
        footer {
            visibility: hidden;
        }
    </style>
    """, unsafe_allow_html=True)

# Google Sheet URL
url = "https://docs.google.com/spreadsheets/d/150YSDU3o1SiEM1WHpPEK9pNPnGUu03qxR26H77RnApw/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

# --- COMMISSIONER CONTROLS ---
signups_open = True 

# 2. SAVE FUNCTION
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
# --- TAB 1: LEADERBOARD ---
# --- TAB 1: LEADERBOARD ---
with tab1:
    st.header("🏆 2026 League Standings")
    try:
        # 1. Read data from Google Sheets
        df_leaderboard = conn.read(spreadsheet=url, ttl=0)
        
        if not df_leaderboard.empty:
            # 2. Data Cleaning & Fill Blanks
            df_leaderboard['Current Score'] = pd.to_numeric(df_leaderboard.get('Current Score', 0)).fillna(0).astype(int)
            df_leaderboard['Total Winnings'] = pd.to_numeric(df_leaderboard.get('Total Winnings', 0)).fillna(0.0)
            # Ensure Previous Pos is numeric
            df_leaderboard['Previous Pos'] = pd.to_numeric(df_leaderboard.get('Previous Pos', 0)).fillna(0).astype(int)
            
            # 3. Sort by Score (Primary) and Winnings (Secondary)
            df_leaderboard = df_leaderboard.sort_values(by=['Current Score', 'Total Winnings'], ascending=False)
            
            # 4. Create the formatted Position column: (Last Pos) Current Pos
            # Example: (18) 1.
            current_positions = range(1, len(df_leaderboard) + 1)
            formatted_pos = []
            
            for last_pos, curr_pos in zip(df_leaderboard['Previous Pos'], current_positions):
                # If last_pos is 0 (new entry), we show (-) instead of (0)
                last_pos_str = str(last_pos) if last_pos > 0 else "-"
                formatted_pos.append(f"({last_pos_str}) {curr_pos}.")
            
            df_leaderboard['Pos'] = formatted_pos
            
            # 5. Column Selection
            # Removed 'Total Pot Distributed' metric as requested.
            desired_cols = ['Pos', 'Name', 'Nickname', 'Current Score', 'Total Winnings']
            available_cols = [c for c in desired_cols if c in df_leaderboard.columns]
            
            # 6. Display with Currency Formatting
            st.dataframe(
                df_leaderboard[available_cols].style.format({
                    "Total Winnings": "£{:.2f}",
                    "Current Score": "{:,}"
                }),
                hide_index=True,
                use_container_width=True
            )
            
            mod_time = datetime.datetime.now().strftime('%d %b %Y, %H:%M')
            st.caption(f"🕒 Last Updated: {mod_time}")
            
        else:
            st.info("No entries yet. Be the first to join in the Signup tab!")
            
    except Exception as e:
        st.error(f"Error loading leaderboard: {e}")
        st.info("The leaderboard is currently empty or the sheet is missing headers.")# --- TAB 2: SIGNUP ---
with tab2:
    st.header("📜 Rules & Signup")

    if not signups_open:
        st.error("🚫 Season Signups are now CLOSED. The 2026 Grid is locked!")
    else:
        with st.expander("📜 View 2026 Fantasy League Rules"):
            st.write("""
            ### How to Score Points (29th Year Rules):
            * **Starting Grid:** 20 pts for 1st, 19 for 2nd... down to 1 pt.
            * **Laps:** 1 point for every lap completed.
            * **Overtaking:** 1 point for every position gained from Grid to Finish.
            * **Finishing:** ONLY if driver/constructor takes the Chequered Flag.
            * **Fastest Lap:** 25 points!
            * **Constructors:** Only your highest-placed car scores finishing points.
            """)

        with st.form("signup_form", clear_on_submit=True):
            st.subheader("2026 Season Selections")
            name = st.text_input("Full Name")
            nickname = st.text_input("Team Nickname")
            email = st.text_input("Email")
            
            col1, col2 = st.columns(2)
            with col1:
                g_a = st.multiselect("GROUP A (Pick 2)", ["Charles Leclerc", "George Russell", "Lando Norris", "Max Verstappen"], max_selections=2)
                g_b = st.multiselect("GROUP B (Pick 2)", ["Fernando Alonso", "Kimi Antonelli", "Lewis Hamilton", "Oscar Piastri"], max_selections=2)
                g_c = st.selectbox("GROUP C (Pick 1)", ["Carlos Sainz Jnr", "Isack Hadjar", "Pierre Gasly"], index=None)
                g_d = st.selectbox("GROUP D (Pick 1)", ["Alex Albon", "Lance Stroll"], index=None)
                g_e = st.selectbox("GROUP E (Pick 1)", ["Esteban Ocon", "Liam Lawson", "Oliver Bearman"], index=None)
                g_f = st.selectbox("GROUP F (Pick 1)", ["Arvid Lindblad", "Nico Hulkenberg"], index=None)
                g_g = st.selectbox("GROUP G (Pick 1)", ["Franco Colapinto", "Gabriel Bortoleto"], index=None)
                g_h = st.selectbox("GROUP H (Pick 1)", ["Sergio Perez", "Valtteri Bottas"], index=None)

            with col2:
                g_i = st.multiselect("GROUP I (Pick 2)", ["Ferrari", "McLaren", "Mercedes"], max_selections=2)
                g_j = st.selectbox("GROUP J (Pick 1)", ["Aston Martin", "Red Bull"], index=None)
                g_k = st.selectbox("GROUP K (Pick 1)", ["Alpine", "Williams"], index=None)
                g_l = st.selectbox("GROUP L (Pick 1)", ["Audi", "Haas"], index=None)
                g_m = st.selectbox("GROUP M (Pick 1)", ["Cadillac", "Racing Bulls"], index=None)

            rules_check = st.checkbox("I agree to the rules and the entry fee.")
            
            if st.form_submit_button("Submit Team"):
                required_selections = [g_c, g_d, g_e, g_f, g_g, g_h, g_j, g_k, g_l, g_m]
                if not rules_check:
                    st.error("You must agree to the rules to join.")
                elif None in required_selections or not name or not nickname:
                    st.error("Please fill in all fields.")
                elif len(g_a) != 2 or len(g_b) != 2 or len(g_i) != 2:
                    st.error("Select exactly TWO for Groups A, B, and I.")
                else:
                    all_picks = g_a + g_b + [g_c, g_d, g_e, g_f, g_g, g_h] + g_i + [g_j, g_k, g_l, g_m]
                    new_entry_data = {
                        "Name": name, "Nickname": nickname, "Email": email,
                        "Picks": str(all_picks), "Current Score": 0, "Total Winnings": 0,
                        "Pos": 0, "Previous Pos": 0
                    }
                    if save_to_gsheet(new_entry_data):
                        st.success(f"✅ Registration successful!")

# --- TAB 3: ADMIN ---
with tab3:
    st.subheader("🔐 Commissioner Access")
    admin_pw = st.text_input("Enter Admin Password", type="password", key="admin_login")
    
    if admin_pw == "admin12345":
        st.success("Welcome back, Commissioner!")
        st.divider()
        
        races_2026 = ["Australia", "China", "Japan", "Bahrain", "Saudi Arabia", "Miami", "Canada", "Monaco", "Barcelona-Catalunya", "Austria", "Great Britain", "Belgium", "Hungary", "Netherlands", "Italy", "Spain", "Azerbaijan", "Singapore", "United States", "Mexico City", "Brazil", "Las Vegas", "Qatar", "Abu Dhabi"]

        col1, col2 = st.columns(2)
        with col1:
            st.write("### 🏁 Race Operations")
            selected_race = st.selectbox("Select Race to Sync", races_2026)
            
            st.write("#### 💰 Race Payouts (£/€)")
            p_cols = st.columns(5)
            w1 = p_cols[0].number_input("1st", value=40, step=5)
            w2 = p_cols[1].number_input("2nd", value=30, step=5)
            w3 = p_cols[2].number_input("3rd", value=25, step=5)
            w4 = p_cols[3].number_input("4th", value=20, step=5)
            w5 = p_cols[4].number_input("5th", value=15, step=5)
            
            if st.button(f"🔄 Sync {selected_race} Results"):
                with st.spinner("Updating scores..."):
                    prizes = [w1, w2, w3, w4, w5]
                    result_msg = scoring_engine.run_sync(conn, url, 2026, selected_race, race_payouts=prizes)
                    if "Successfully" in result_msg:
                        st.balloons()
                        st.success(result_msg)
                    else:
                        st.error(result_msg)

        with col2:
            st.write("### 🧪 Pre-Season Testing")
            st.info("Bypass API and test Sheet connection with mock data.")
            if st.button("🚀 Run System Stress Test"):
                with st.spinner("Testing logic..."):
                    test_prizes = [50, 40, 30, 20, 10]
                    msg = scoring_engine.run_sync(conn, url, 2026, "Test", race_payouts=test_prizes, is_test=True)
                    if "Successfully" in msg:
                        st.toast("Test Successful!", icon="✅")
                        st.success("Math and Connection Verified.")
                    else:
                        st.error(msg)

            st.write("### ⚠️ Danger Zone")
            if st.button("🗑️ RESET LEAGUE (Wipe Sheet)"):
                empty_df = pd.DataFrame(columns=['Name', 'Nickname', 'Email', 'Picks', 'Current Score', 'Total Winnings', 'Pos', 'Previous Pos'])
                conn.update(spreadsheet=url, data=empty_df)
                st.warning("Data wiped!")
                st.rerun()
                
    elif admin_pw != "":

        st.error("Incorrect Password.")
