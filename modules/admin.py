import streamlit as st
import pandas as pd
import datetime
import scoring_engine

def show_admin_panel(conn, url):
    st.subheader("🔐 Commissioner Access")
    admin_pw = st.text_input("Enter Admin Password", type="password", key="admin_login")
    
    if admin_pw == "admin12345":
        st.success("Welcome back, Commissioner!")
        st.divider()
        
        races_2026 = [
            "Australia", "China", "Japan", "Bahrain", "Saudi Arabia", "Miami", 
            "Canada", "Monaco", "Barcelona-Catalunya", "Austria", "Great Britain", 
            "Belgium", "Hungary", "Netherlands", "Italy", "Spain", "Azerbaijan", 
            "Singapore", "United States", "Mexico City", "Brazil", "Las Vegas", 
            "Qatar", "Abu Dhabi"
        ]

        # --- NOTICE BOARD SECTION ---
        st.write("### 📢 League Notice Board")
        notice_msg = st.text_area("Enter a message for the Leaderboard (leave empty to clear):")
        if st.button("Update Notice"):
            df_notice = pd.DataFrame({'Message': [notice_msg]})
            try:
                conn.update(spreadsheet=url, worksheet="Notices", data=df_notice)
                st.success("Notice updated! It will now appear on the Leaderboard.")
            except Exception as e:
                st.error(f"Error updating notice: {e}")
                st.info("⚠️ Ensure you have created a tab named 'Notices' in your Google Sheet.")
        
        st.divider()

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
                        # Freeze current positions before adding new race points
                        df_current['Previous Pos'] = df_current['Current Score'].rank(ascending=False, method='min').fillna(0).astype(int)
                        conn.update(spreadsheet=url, data=df_current)

                    # 2. Run Sync via Scoring Engine
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
                    # Pass is_test=True to bypass FastF1 API
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
                # Reset with the updated column structure
                empty_df = pd.DataFrame(columns=[
                    'Name', 'Nickname', 'Email', 'Picks', 'Current Score', 
                    'Total Winnings', 'Pos', 'Previous Pos', 'Last Race Pts'
                ])
                conn.update(spreadsheet=url, data=empty_df)
                st.warning("Data wiped!")
                st.rerun()
                
    elif admin_pw != "":
        st.error("Incorrect Password.")
