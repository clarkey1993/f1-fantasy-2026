import streamlit as st
import pandas as pd
import ast
import datetime
from modules.player_dashboard import render_card

def show_player_profile(df, player_name):
    # Filter for the specific player
    # Use strip() to handle accidental trailing spaces in names
    player_row = df[df['Name'].astype(str).str.strip() == str(player_name).strip()]
    
    if player_row.empty:
        st.error(f"Player '{player_name}' not found.")
        if st.button("Back to Leaderboard"):
            st.query_params.clear()
            st.rerun()
        return

    row = player_row.iloc[0]
    
    if st.button("← Back to Leaderboard"):
        st.query_params.clear()
        st.rerun()

    st.title(f"🏎️ {row['Nickname']}'s Team")
    st.write(f"**Manager:** {row['Name']}")
    
    if 'Picks' in row and pd.notna(row['Picks']):
        try:
            # Clean the string to handle "Smart Quotes" or manual entry errors
            raw_picks = str(row['Picks']).strip()
            raw_picks = raw_picks.replace('“', '"').replace('”', '"').replace("‘", "'").replace("’", "'")
            
            picks_list = ast.literal_eval(raw_picks)
            
            if not isinstance(picks_list, list):
                st.warning("Picks data format is incorrect (not a list).")
                return

            drivers = picks_list[:10]
            constructors = picks_list[10:]
            
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("Drivers")
                d1, d2 = st.columns(2)
                for i, d in enumerate(drivers):
                    if i % 2 == 0:
                        d1.markdown(render_card(d, is_constructor=False), unsafe_allow_html=True)
                    else:
                        d2.markdown(render_card(d, is_constructor=False), unsafe_allow_html=True)
            with c2:
                st.subheader("Constructors")
                con1, con2 = st.columns(2)
                for i, c in enumerate(constructors):
                    if i % 2 == 0:
                        con1.markdown(render_card(c, is_constructor=True), unsafe_allow_html=True)
                    else:
                        con2.markdown(render_card(c, is_constructor=True), unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Could not load picks: {e}")
            st.caption(f"Raw Data: {row.get('Picks', 'N/A')}")
    else:
        st.info("No picks available.")

def show_leaderboard(conn, url):
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

            # --- CHECK FOR DRILL-DOWN VIEW ---
            # If a player is selected via query param, show their profile instead of the main table
            if "player" in st.query_params:
                show_player_profile(df, st.query_params["player"])
                return

            # --- NOTICE BOARD ---
            try:
                # Attempt to read from the 'Notices' tab
                df_notice = conn.read(spreadsheet=url, worksheet="Notices", ttl=0)
                if not df_notice.empty and 'Message' in df_notice.columns:
                    msg = str(df_notice.iloc[0]['Message'])
                    if msg and msg.strip() != "" and msg.lower() != "nan":
                        st.warning(f"📢 **League Notice:** {msg}")
            except:
                pass # Fail silently if the tab doesn't exist yet

            current_year = datetime.datetime.now().year
            st.header(f"🏆 {current_year} League Standings")

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
                    width='stretch'
                )

            with col_right:
                st.markdown("**Weekend Payouts**")
                # Showing the top 5 earners based on total winnings
                latest_wins_df = df[df['Total Winnings'] > 0].sort_values(by='Total Winnings', ascending=False).head(5)
                if not latest_wins_df.empty:
                    st.dataframe(
                        latest_wins_df[['Nickname', 'Total Winnings']].style.format({"Total Winnings": "£/€{:.2f}"}), 
                        hide_index=True, 
                        width='stretch'
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
            
            # Add Link Column for Drill-down
            # We create a relative URL query string: ?player=Name
            df_leaderboard['Team Sheet'] = df_leaderboard['Name'].apply(lambda x: f"?player={x}")

            # 5. Column Selection
            desired_cols = ['Pos', 'Name', 'Nickname', 'Current Score', 'Total Winnings', 'Team Sheet']
            available_cols = [c for c in desired_cols if c in df_leaderboard.columns]
            
            # 6. Display Main Leaderboard
            st.dataframe(
                df_leaderboard[available_cols],
                hide_index=True,
                width='stretch',
                column_config={
                    "Team Sheet": st.column_config.LinkColumn("Selections", display_text="View Team")
                }
            )
            
            mod_time = datetime.datetime.now().strftime('%d %b %Y, %H:%M')
            st.caption(f"🕒 Last Updated: {mod_time}")
            
        else:
            st.info("No entries yet. Be the first to join in the Signup tab!")
            
    except Exception as e:
        st.error(f"Error loading leaderboard: {e}")
        st.info("Ensure your Google Sheet headers match: Name, Nickname, Current Score, Total Winnings, Previous Pos, Last Race Pts")