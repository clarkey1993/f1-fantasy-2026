import streamlit as st
import pandas as pd
import datetime
import scoring_engine
import shutil
import os

def show_admin_panel(conn, url):
    st.subheader("🔐 Commissioner Access")
    st.success("Welcome back, Commissioner!")
    st.divider()
    
    current_year = datetime.datetime.now().year
    races_list = [
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
        selected_race = st.selectbox("Select Race to Sync", races_list)
        
        st.write("#### 💰 Race Payouts (£/€)")
        p_cols = st.columns(4)
        w1 = p_cols[0].number_input("1st", value=20, step=5)
        w2 = p_cols[1].number_input("2nd", value=15, step=5)
        w3 = p_cols[2].number_input("3rd", value=10, step=5)
        w_rest = p_cols[3].number_input("4th - 12th", value=5, step=5)
        
        if st.button(f"🔄 Sync {selected_race} & Update Positions"):
            with st.spinner(f"Syncing {selected_race}..."):
                # Run Sync via Scoring Engine (Snapshotting happens inside now)
                prizes = [w1, w2, w3] + [w_rest] * 9
                result_msg = scoring_engine.run_sync(conn, url, current_year, selected_race, race_payouts=prizes)
                
                if "Successfully" in result_msg:
                    st.balloons()
                    st.success(result_msg)
                else:
                    st.error(result_msg)

    with col2:
        st.write("### 🧪 Pre-Season Testing")
        st.info("Test connection using a random race from the 2025 season.")
        
        if st.button("🚀 Run System Stress Test"):
            with st.spinner("Simulating race and testing logic..."):
                # Use test payouts
                test_prizes = [20, 15, 10] + [5] * 9
                # Pass is_test=True to bypass FastF1 API
                msg = scoring_engine.run_sync(conn, url, current_year, "Test Race", race_payouts=test_prizes, is_test=True)
                
                if "Successfully" in msg:
                    st.toast("Test Successful!", icon="✅")
                    st.success("Test points and payouts applied to the sheet.")
                else:
                    st.error(msg)

        st.write("### 🛠️ Troubleshooting")
        if st.button("🧹 Clear FastF1 Cache"):
            try:
                if os.path.exists('f1_cache'):
                    shutil.rmtree('f1_cache')
                st.success("Cache cleared! Next sync will download fresh data from F1.")
            except Exception as e:
                st.error(f"Error clearing cache: {e}")

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
                'Name', 'Nickname', 'Email', 'Password', 'Picks', 'Current Score', 
                'Total Winnings', 'Pos', 'Previous Pos', 'Last Race Pts', 'Total Spent'
            ])
            conn.update(spreadsheet=url, data=empty_df)
            st.warning("Data wiped!")
            st.rerun()
