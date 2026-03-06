import streamlit as st
import pandas as pd
import requests

def show_f1_standings():
    st.header("🏎️ Current F1 Standings")
    
    try:
        # 1. Fetch Drivers Standings
        # Use Jolpica mirror (Ergast replacement) for better stability
        url_d = "https://api.jolpi.ca/ergast/f1/current/driverStandings.json"
        res_d = requests.get(url_d, timeout=5)
        data_d = res_d.json()
        
        # Check if season has started
        standings_list_d = data_d['MRData']['StandingsTable']['StandingsLists']
        
        if not standings_list_d:
            st.info("No standings available yet for the current season.")
            return

        drivers = standings_list_d[0]['DriverStandings']
        
        d_rows = []
        for d in drivers:
            d_rows.append({
                "Pos": d['position'],
                "Driver": f"{d['Driver']['givenName']} {d['Driver']['familyName']}",
                "Team": d['Constructors'][0]['name'] if d['Constructors'] else "Free Agent",
                "Pts": d['points']
            })
        
        df_drivers = pd.DataFrame(d_rows)

        # 2. Fetch Constructors Standings
        url_c = "https://api.jolpi.ca/ergast/f1/current/constructorStandings.json"
        res_c = requests.get(url_c, timeout=5)
        data_c = res_c.json()
        
        standings_list_c = data_c['MRData']['StandingsTable']['StandingsLists']
        constructors = standings_list_c[0]['ConstructorStandings']
        
        c_rows = []
        for c in constructors:
            c_rows.append({
                "Pos": c['position'],
                "Team": c['Constructor']['name'],
                "Pts": c['points']
            })
            
        df_const = pd.DataFrame(c_rows)

        # 3. Display Side-by-Side
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Drivers Championship")
            st.dataframe(df_drivers, hide_index=True, use_container_width=True)
            
        with col2:
            st.subheader("Constructors Championship")
            st.dataframe(df_const, hide_index=True, use_container_width=True)

    except Exception as e:
        st.warning("⚠️ Could not connect to live F1 data source.")
        with st.expander("View Error Details"):
            st.error(f"{e}")