import streamlit as st
import pandas as pd
import ast
import datetime

def show_leaderboard(conn, url):
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
                # Showing the top 5 earners based on total winnings
                latest_wins_df = df[df['Total Winnings'] > 0].sort_values(by='Total Winnings', ascending=False).head(5)
                if not latest_wins_df.empty:
                    st.dataframe(
                        latest_wins_df[['Nickname', 'Total Winnings']].style.format({"Total Winnings": "£/€{:.2f}"}), 
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
            for index, row in df_leaderboard.iterrows():
                expander_label = f"{row['Pos']} **{row['Nickname']}** - {row['Current Score']:,} pts"
                with st.expander(expander_label):
                    # Display other info and picks inside
                    st.markdown(f"**Full Name:** {row['Name']}")
                    st.markdown(f"**Total Winnings:** £/€{row['Total Winnings']:.2f}")
                    
                    if 'Picks' in row and pd.notna(row['Picks']):
                        try:
                            # The 'Picks' column is a string representation of a list
                            picks_list = ast.literal_eval(row['Picks'])
                            drivers = picks_list[:10]
                            constructors = picks_list[10:]
                            
                            p_col1, p_col2 = st.columns(2)
                            with p_col1:
                                st.markdown("**Drivers**")
                                st.dataframe(pd.DataFrame({'Driver': drivers}), hide_index=True, use_container_width=True)
                            with p_col2:
                                st.markdown("**Constructors**")
                                st.dataframe(pd.DataFrame({'Constructor': constructors}), hide_index=True, use_container_width=True)

                        except (ValueError, SyntaxError):
                            st.warning("Could not display picks for this user (invalid format).")
                        except Exception as e:
                            st.warning(f"Picks not available. Error: {e}")
                    else:
                        st.info("No picks recorded for this entry.")
            
            mod_time = datetime.datetime.now().strftime('%d %b %Y, %H:%M')
            st.caption(f"🕒 Last Updated: {mod_time}")
            
        else:
            st.info("No entries yet. Be the first to join in the Signup tab!")
            
    except Exception as e:
        st.error(f"Error loading leaderboard: {e}")
        st.info("Ensure your Google Sheet headers match: Name, Nickname, Current Score, Total Winnings, Previous Pos, Last Race Pts")