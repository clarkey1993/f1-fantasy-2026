import streamlit as st
import pandas as pd
import os
import datetime
import scoring_engine
from streamlit_gsheets import GSheetsConnection

# 1. SETUP & CONNECTION
st.set_page_config(page_title="F1 Fantasy 2026", layout="wide")

# --- CUSTOM THEME STYLING (Fixes white top/bottom & mobile look) ---
st.markdown("""
    <style>
        .stApp { background-color: #0E1117; }
        header { visibility: hidden; }
        footer { visibility: hidden; }
        .main { background-color: #0E1117; }
        /* Make tabs easier to tap on mobile */
        .stTabs [data-baseweb="tab"] { font-size: 18px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# Google Sheet URL
url = "https://docs.google.com/spreadsheets/d/150YSDU3o1SiEM1WHpPEK9pNPnGUu03qxR26H77RnApw/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

# --- COMMISSIONER CONTROLS ---
deadline = datetime.datetime(2026, 3, 8, 5, 0)
now = datetime.datetime.now()
signups_open = now < deadline 

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
with tab1:
    st.header("🏆 2026 League Standings")
    try:
        # 1. Read data from Google Sheets
        df = conn.read(spreadsheet=url, ttl=0)
        
        if not df.empty:
            # 2. Data Cleaning & Fill Blanks (FIXED LOGIC)
            # We force columns to numeric and handle missing columns gracefully
            cols_to_fix = {
                'Current Score': 0,
                'Total Winnings': 0.0,
                'Previous Pos': 0,
                'Last Race Pts': 0
            }
            
            for col, default in cols_to_fix.items():
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(default)
                else:
                    df[col] = default

            # Ensure integer types for scores and positions
            df['Current Score'] = df['Current Score'].astype(int)
            df['Previous Pos'] = df['Previous Pos'].astype(int)
            df['Last Race Pts'] = df['Last Race Pts'].astype(int)

            # --- SECTION A: LATEST RACE RECAP (December Style) ---
            st.subheader("🏁 Latest Race Results")
            col_left, col_right = st.columns(2)
            
            with col_left:
                st.markdown("**Top Points This Weekend**")
                # Sort by the most recent race points only
                latest_pts_df = df.sort_values(by='Last Race Pts', ascending=False).head(5)
                st.dataframe(
                    latest_pts_df[['Nickname', 'Last Race Pts']], 
                    hide_index=True, 
                    use_container_width=True
                )

            with col_right:
                st.markdown("**Weekend Payouts**")
                # Showing the top 5 earners based on total winnings (or weekend wins if you track them)
                latest_wins_df = df[df['Total Winnings'] > 0].sort_values(by='Total Winnings', ascending=False).head(5)
                if not latest_wins_df.empty:
                    st.dataframe(
                        latest_wins_df[['Nickname', 'Total Winnings']].style.format({"Total Winnings": "£{:.2f}"}), 
                        hide_index=True, 
                        use_container_width=True
                    )
                else:
                    st.info("No payouts for this round yet.")
            
            st.divider()

            # --- SECTION B: OVERALL CHAMPIONSHIP ---
            st.subheader("🏆 Overall Standings")
            
            # 3. Sort by Total Score (Primary) and Winnings (Secondary)
            df_leaderboard = df.sort_values(by=['Current Score', 'Total Winnings'], ascending=False).copy()
            
            # 4. Create the formatted Position column: (Last Pos) Current Pos
            current_positions = range(1, len(df_leaderboard) + 1)
            formatted_pos = []
            
            for last_pos, curr_pos in zip(df_leaderboard['Previous Pos'], current_positions):
                last_pos_str = str(int(last_pos)) if last_pos > 0 else "-"
                formatted_pos.append(f"({last_pos_str}) {curr_pos}.")
            
            df_leaderboard['Pos'] = formatted_pos
            
            # 5. Column Selection
            desired_cols = ['Pos', 'Name', 'Nickname', 'Current Score', 'Total Winnings']
            available_cols = [c for c in desired_cols if c in df_leaderboard.columns]
            
            # 6. Display Main Leaderboard
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
        st.info("Ensure your Google Sheet headers match: Name, Nickname, Current Score, Total Winnings, Previous Pos, Last Race Pts")# --- TAB 2: SIGNUP ---
with tab2:
    st.header("📜 Rules & Signup")

    # 1. Calculate Countdown
    # Deadline: Saturday March 8, 2026 at 5:00 AM UK Time
    deadline = datetime.datetime(2026, 3, 8, 5, 0)
    now = datetime.datetime.now()
    
    if now < deadline:
        time_left = deadline - now
        days = time_left.days
        hours, remainder = divmod(time_left.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        st.info(f"⏳ **Countdown!!:** {days}d {hours}h {minutes}m until the 2026 Grid is set!")
    
    # 2. Check if Signups are open (Uses the automatic clock)
    signups_open_auto = now < deadline

    if not signups_open_auto:
        st.error("🚫 Season Signups are now CLOSED. The 2026 Grid is locked! (Deadline: March 8, 05:00 AM)")
        
        # We still show the rules even when closed
        with st.expander("📜 View 2026 Fantasy League Rules"):
            st.write("""
            ### 29th Year Rules Summary:
            * **Entry Fee:** £5 (or Euros).
            * **Team Structure:** 10 Drivers and 6 Constructors.
            * **Starting Grid:** 20 pts for 1st, down to 1 pt for 20th.
            * **Laps:** 1 point for every lap completed.
            * **Improvement:** 1 point for every position gained from Grid to Finish.
            * **Finishing:** Points awarded ONLY if you take the Chequered Flag.
            * **Fastest Lap:** 25 points.
            * **Constructors:** 10 pts per car finished; only your highest-placed car scores finishing position points.
            """)
    else:
        with st.expander("📜 View 2026 Fantasy League Rules"):
            st.write("""
            ### How to Score Points (29th Year Rules):
            * **The Team:** Your 10 drivers and 6 teams form your squad for the **whole of the 2026 season.**
            * **Starting Grid:** Points for actual starting grid positions (20 for 1st, 19 for 2nd... down to 1).
            * **Laps:** 1 point for every lap completed.
            * **Improvement:** 1 point for every position gained from Grid to Finish.
            * **Finishing:** ONLY if driver/constructor takes the Chequered Flag.
            * **Fastest Lap:** 25 points!
            * **Constructors:** 10 pts for every car that finishes + finishing points for your best car.
            * **Entry:** £5 / €5 entry fee.
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

            rules_check = st.checkbox("I agree to the rules and the £5 / €5 per race fee.")
            
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
                        st.balloons()
                        st.success(f"✅ Registration successful! Good luck for the 2026 season.")# --- TAB 3: ADMIN ---
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
            
            if st.button(f"🔄 Sync {selected_race} & Update Positions"):
                with st.spinner(f"Syncing {selected_race}..."):
                    # 1. Snapshot Ranks
                    df_current = conn.read(spreadsheet=url, ttl=0)
                    if not df_current.empty:
                        df_current['Previous Pos'] = df_current['Current Score'].rank(ascending=False, method='min').fillna(0).astype(int)
                        conn.update(spreadsheet=url, data=df_current)

                    # 2. Run Sync
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
                with st.spinner("Simulating race and testing logic..."):
                    # Use test payouts
                    test_prizes = [50, 40, 30, 20, 10]
                    # We pass is_test=True to the scoring engine
                    msg = scoring_engine.run_sync(conn, url, 2026, "Test Race", race_payouts=test_prizes, is_test=True)
                    
                    if "Successfully" in msg:
                        st.toast("Test Successful!", icon="✅")
                        st.success("Test points and payouts applied to the sheet.")
                    else:
                        st.error(msg)

            st.divider()
            st.write("### 📂 Data Management")
            df_export = conn.read(spreadsheet=url, ttl=0)
            if not df_export.empty:
                csv = df_export.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download League Backup (CSV)",
                    data=csv,
                    file_name=f"f1_fantasy_backup_{datetime.datetime.now().strftime('%Y%m%d')}.csv",
                    mime='text/csv',
                )

            st.write("### ⚠️ Danger Zone")
            if st.button("🗑️ RESET LEAGUE (Wipe Sheet)"):
                empty_df = pd.DataFrame(columns=['Name', 'Nickname', 'Email', 'Picks', 'Current Score', 'Total Winnings', 'Pos', 'Previous Pos', 'Last Race Pts'])
                conn.update(spreadsheet=url, data=empty_df)
                st.warning("Data wiped!")
                st.rerun()
                
    elif admin_pw != "":
        st.error("Incorrect Password.")