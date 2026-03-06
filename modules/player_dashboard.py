import streamlit as st
import pandas as pd
import ast

def show_dashboard(conn, url):
    # Initialize session state for user login
    if 'user_nick' not in st.session_state:
        st.session_state.user_nick = None

    # --- NOT LOGGED IN: SHOW LOGIN FORM ---
    if st.session_state.user_nick is None:
        st.header("👤 Player Login")
        st.caption("Access your private dashboard to see your team and stats.")
        
        with st.form("login_form"):
            user = st.text_input("Team Nickname")
            pw = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Log In")
            
            if submitted:
                try:
                    df = conn.read(spreadsheet=url, ttl=0)
                    
                    if 'Password' not in df.columns:
                        st.error("System Error: Password column missing in database. Please ask Admin to reset the sheet.")
                    else:
                        # Find user (case-insensitive search)
                        user_row = df[df['Nickname'].astype(str).str.strip().str.lower() == user.strip().lower()]
                        
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
            
            # Key Stats
            c1, c2, c3 = st.columns(3)
            c1.metric("🏆 Rank", f"#{int(user_row['Pos'])}")
            c2.metric("📊 Total Points", int(user_row['Current Score']))
            c3.metric("💰 Winnings", f"£/€{float(user_row['Total Winnings']):.2f}")
            
            st.subheader("🏎️ Your 2026 Lineup")
            if pd.notna(user_row['Picks']):
                raw_picks = str(user_row['Picks']).strip().replace('“', '"').replace('”', '"').replace("‘", "'").replace("’", "'")
                picks = ast.literal_eval(raw_picks)
                
                drivers = picks[:10]
                constructors = picks[10:]
                
                col_d, col_c = st.columns(2)
                with col_d:
                    st.info("**Drivers**\n\n" + "\n".join([f"• {d}" for d in drivers]))
                with col_c:
                    st.success("**Constructors**\n\n" + "\n".join([f"• {c}" for c in constructors]))
        except Exception as e:
            st.error(f"Error loading dashboard: {e}")