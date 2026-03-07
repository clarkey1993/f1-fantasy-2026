import streamlit as st
import datetime
import pandas as pd
import ast

def show_signup_form(conn, url, save_to_gsheet_func):
    st.header("📜 Rules & Signup")

    # 1. Calculate Countdown
    # Deadline: Saturday March 8 at 5:00 AM UK Time (Current Year)
    current_year = datetime.datetime.now().year
    deadline = datetime.datetime(current_year, 3, 8, 5, 0)
    now = datetime.datetime.now()
    
    if now < deadline:
        time_left = deadline - now
        days = time_left.days
        hours, remainder = divmod(time_left.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        st.info(f"⏳ **Countdown!!:** {days}d {hours}h {minutes}m until the {current_year} Grid is set!")
    
    # 2. Check if Signups are open (Uses the automatic clock)
    signups_open_auto = now < deadline

    if not signups_open_auto:
        st.error(f"🚫 Season Signups are now CLOSED. The {current_year} Grid is locked! (Deadline: March 8, 05:00 AM)")
        
        # We still show the rules even when closed
        with st.expander(f"📜 View {current_year} Fantasy League Rules"):
            st.write(f"""
            ### {current_year} Rules Summary:
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
        with st.expander(f"📜 View {current_year} Fantasy League Rules"):
            st.write(f"""
            ### How to Score Points:
            * **The Team:** Your 10 drivers and 6 teams form your squad for the **whole of the {current_year} season.**
            * **Starting Grid:** Points for actual starting grid positions (20 for 1st, 19 for 2nd... down to 1).
            * **Laps:** 1 point for every lap completed.
            * **Improvement:** 1 point for every position gained from Grid to Finish.
            * **Finishing:** ONLY if driver/constructor takes the Chequered Flag.
            * **Fastest Lap:** 25 points!
            * **Constructors:** 10 pts for every car that finishes + finishing points for your best car.
            * **Entry:** £5 / €5 entry fee.
            """)

        with st.form("signup_form", clear_on_submit=False):
            st.subheader(f"{current_year} Season Selections")
            name = st.text_input("Full Name", key="signup_name")
            nickname = st.text_input("Team Nickname", key="signup_nickname")
            password = st.text_input("Create a Password", type="password", key="signup_password")
            email = st.text_input("Email", key="signup_email")
            
            col1, col2 = st.columns(2)
            with col1:
                g_a = st.multiselect("GROUP A (Pick 2)", ["Charles Leclerc", "George Russell", "Lando Norris", "Max Verstappen"], max_selections=2, key="signup_g_a")
                g_b = st.multiselect("GROUP B (Pick 2)", ["Fernando Alonso", "Kimi Antonelli", "Lewis Hamilton", "Oscar Piastri"], max_selections=2, key="signup_g_b")
                g_c = st.selectbox("GROUP C (Pick 1)", ["Carlos Sainz Jnr", "Isack Hadjar", "Pierre Gasly"], index=None, key="signup_g_c")
                g_d = st.selectbox("GROUP D (Pick 1)", ["Alex Albon", "Lance Stroll"], index=None, key="signup_g_d")
                g_e = st.selectbox("GROUP E (Pick 1)", ["Esteban Ocon", "Liam Lawson", "Oliver Bearman"], index=None, key="signup_g_e")
                g_f = st.selectbox("GROUP F (Pick 1)", ["Arvid Lindblad", "Nico Hulkenberg"], index=None, key="signup_g_f")
                g_g = st.selectbox("GROUP G (Pick 1)", ["Franco Colapinto", "Gabriel Bortoleto"], index=None, key="signup_g_g")
                g_h = st.selectbox("GROUP H (Pick 1)", ["Sergio Perez", "Valtteri Bottas"], index=None, key="signup_g_h")

            with col2:
                g_i = st.multiselect("GROUP I (Pick 2)", ["Ferrari", "McLaren", "Mercedes"], max_selections=2, key="signup_g_i")
                g_j = st.selectbox("GROUP J (Pick 1)", ["Aston Martin", "Red Bull"], index=None, key="signup_g_j")
                g_k = st.selectbox("GROUP K (Pick 1)", ["Alpine", "Williams"], index=None, key="signup_g_k")
                g_l = st.selectbox("GROUP L (Pick 1)", ["Audi", "Haas"], index=None, key="signup_g_l")
                g_m = st.selectbox("GROUP M (Pick 1)", ["Cadillac", "Racing Bulls"], index=None, key="signup_g_m")

            rules_check = st.checkbox("I agree to the rules and the £5 / €5 per race fee.", key="signup_rules")
            
            if st.form_submit_button("Submit Team"):
                required_selections = [g_c, g_d, g_e, g_f, g_g, g_h, g_j, g_k, g_l, g_m]
                if not rules_check:
                    st.error("You must agree to the rules to join.")
                elif None in required_selections or not name or not nickname or not password:
                    st.error("Please fill in all fields.")
                elif len(g_a) != 2 or len(g_b) != 2 or len(g_i) != 2:
                    st.error("Select exactly TWO for Groups A, B, and I.")
                else:
                    all_picks = g_a + g_b + [g_c, g_d, g_e, g_f, g_g, g_h] + g_i + [g_j, g_k, g_l, g_m]
                    
                    # --- DUPLICATE TEAM CHECK ---
                    try:
                        existing_df = conn.read(spreadsheet=url, ttl=0)
                        if not existing_df.empty and 'Picks' in existing_df.columns:
                            new_picks_set = set(all_picks)
                            for _, row in existing_df.iterrows():
                                if pd.notna(row['Picks']):
                                    try:
                                        # Clean smart quotes and parse
                                        clean_picks = str(row['Picks']).replace('“', '"').replace('”', '"').replace("‘", "'").replace("’", "'")
                                        existing_picks_list = ast.literal_eval(clean_picks)
                                        if isinstance(existing_picks_list, list) and set(existing_picks_list) == new_picks_set:
                                            st.error(f"⚠️ Selection Error: This exact team has already been chosen by '{row['Name']}'. Please change at least 1 pick.")
                                            return
                                    except:
                                        continue
                    except Exception as e:
                        st.warning(f"Could not verify uniqueness (Connection Error): {e}")

                    new_entry_data = {
                        "Name": name, "Nickname": nickname, "Email": email,
                        "Password": password, "Picks": str(all_picks), "Current Score": 0, "Total Winnings": 0,
                        "Pos": 0, "Previous Pos": 0, "Last Race Pts": 0, "Total Spent": 0
                    }
                    if save_to_gsheet_func(new_entry_data):
                        st.balloons()
                        st.success(f"✅ Registration successful! Good luck for the {current_year} season.")
