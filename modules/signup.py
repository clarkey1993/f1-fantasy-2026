import streamlit as st
import datetime
import pandas as pd

def show_signup_form(conn, url, save_to_gsheet_func):
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
            ### 2026 Rules Summary:
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
            ### How to Score Points:
            * **The Team:** Your 10 drivers and 6 teams form your squad for the **whole of the 2026 season.**
            * **Starting Grid:** Points for actual starting grid positions (20 for 1st, 19 for 2nd... down to 1).
            * **Laps:** 1 point for every lap completed.
            * **Improvement:** 1 point for every position gained from Grid to Finish.
            * **Finishing:** ONLY if driver/constructor takes the Chequered Flag.
            * **Fastest Lap:** 25 points!
            * **Constructors:** 10 pts for every car that finishes + finishing points for your best car.
            * **Entry:** £5 / €5 entry fee.
            """)

        with st.form("signup_form", clear_on_submit=False):
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
                        "Pos": 0, "Previous Pos": 0, "Last Race Pts": 0
                    }
                    if save_to_gsheet_func(new_entry_data):
                        st.balloons()
                        st.success(f"✅ Registration successful! Good luck for the 2026 season.")
