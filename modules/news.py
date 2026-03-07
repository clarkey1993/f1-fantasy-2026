import streamlit as st
import re
import fastf1
import pandas as pd
import datetime

@st.cache_data(ttl=3600)
def get_next_f1_session():
    try:
        # Enable cache for speed
        fastf1.Cache.enable_cache('f1_cache')
        
        now = datetime.datetime.now(datetime.timezone.utc)
        schedule = fastf1.get_event_schedule(now.year, include_testing=False)
        
        for _, event in schedule.iterrows():
            for i in range(1, 6):
                date_col = f'Session{i}DateUtc'
                name_col = f'Session{i}'
                
                if date_col in event and pd.notna(event[date_col]):
                    s_date = event[date_col]
                    if s_date.tzinfo is None:
                        s_date = s_date.replace(tzinfo=datetime.timezone.utc)
                    
                    if s_date > now:
                        return f"{event['EventName']} - {event[name_col]}", s_date
        return None, None
    except:
        return None, None

def show_latest_results():
    """Fetch and display the latest session results."""
    st.subheader("🏎️ Latest Session Results")
    
    with st.spinner("Loading latest track data..."):
        try:
            # Ensure cache is enabled
            fastf1.Cache.enable_cache('f1_cache')
            
            now = datetime.datetime.now(datetime.timezone.utc)
            year = now.year
            
            # Get schedule
            schedule = fastf1.get_event_schedule(year, include_testing=False)
            
            # Fallback to previous year if early in the season
            first_session = schedule['Session1DateUtc'].min() if not schedule.empty else None
            if first_session and first_session.tzinfo is None:
                first_session = first_session.replace(tzinfo=datetime.timezone.utc)

            if schedule.empty or (first_session and first_session > now):
                year -= 1
                schedule = fastf1.get_event_schedule(year, include_testing=False)
            
            # Find the absolute latest session that has occurred
            past_sessions = []
            for i, row in schedule.iterrows():
                for s_num in range(1, 6):
                    date_col = f'Session{s_num}DateUtc'
                    name_col = f'Session{s_num}'
                    if date_col in row and pd.notna(row[date_col]):
                        s_date = row[date_col]
                        if s_date.tzinfo is None:
                            s_date = s_date.replace(tzinfo=datetime.timezone.utc)
                        if s_date < now:
                            past_sessions.append({
                                'date': s_date,
                                'round': row['RoundNumber'],
                                'name': row[name_col],
                                'event': row['EventName']
                            })
            
            if not past_sessions:
                st.info("No recent results available.")
                return

            # Sort by date and pick the latest one
            latest = sorted(past_sessions, key=lambda x: x['date'])[-1]
            
            # Load the session
            session = fastf1.get_session(year, latest['round'], latest['name'])
            session.load(telemetry=False, weather=False, messages=False)
            
            st.markdown(f"**📍 {session.event.EventName} - {session.name}**")
            
            results = session.results
            if results.empty:
                st.warning("Data processing... Results not yet available.")
                return
            
            # Select and Format Columns
            cols = ['Position', 'FullName', 'TeamName']
            
            # Add timing columns based on session type
            if 'Q3' in results.columns: # Qualifying
                cols.extend(['Q1', 'Q2', 'Q3'])
                # Format times to look cleaner (remove "0 days 00:01:..." junk)
                def format_quali(row, col):
                    val = row[col]
                    if pd.notna(val) and str(val).strip() != "":
                        return str(val).split('days ')[-1][:-3]
                    
                    # Handle missing times (DNF/No Time)
                    try:
                        pos = float(row['Position'])
                    except:
                        pos = 20.0 # Fallback
                    
                    status = str(row['Status']) if pd.notna(row['Status']) else "DNF"
                    if status.lower() == 'finished': status = "DNF"
                    
                    if col == 'Q1': return status
                    if col == 'Q2' and pos <= 15: return status
                    if col == 'Q3' and pos <= 10: return status
                    return ""

                for q in ['Q1', 'Q2', 'Q3']:
                    results[q] = results.apply(lambda row: format_quali(row, q), axis=1)
            elif 'Time' in results.columns: # Race
                cols.extend(['Time', 'Points'])
                # If Time is missing (DNF), show the Status (e.g., "Accident", "Engine", "+1 Lap")
                results['Time'] = results.apply(lambda row: str(row['Time']).split('days ')[-1][:-3] if pd.notna(row['Time']) else str(row['Status']), axis=1)
                # Format Points to remove decimals (e.g. "25.0" -> "25")
                results['Points'] = results['Points'].astype(str).replace(r'\.0$', '', regex=True)
            
            # Clean up Position (handle DNFs)
            results['Position'] = results['Position'].fillna(results['ClassifiedPosition'])
            results['Position'] = results['Position'].fillna('DNF')
            results['Position'] = results['Position'].astype(str).replace(r'\.0$', '', regex=True)
            results['Position'] = results['Position'].replace(['nan', 'R', 'N/C', 'Ret', 'None'], 'DNF')
            
            # --- STYLING: Color rows by Team ---
            fallback_colors = {
                "Red Bull Racing": "#3671C6", "Mercedes": "#27F4D2", "Ferrari": "#E80020",
                "McLaren": "#FF8000", "Aston Martin": "#229971", "Alpine": "#0093CC",
                "Williams": "#64C4FF", "RB": "#6692FF", "Haas F1 Team": "#B6BABD",
                "Kick Sauber": "#52E252", "Sauber": "#52E252", "Audi": "#52E252"
            }

            def style_rows(row):
                idx = row.name
                team_name = results.loc[idx, 'TeamName']
                
                # Try FastF1 color first
                hex_color = None
                if 'TeamColor' in results.columns:
                    c = results.loc[idx, 'TeamColor']
                    if pd.notna(c) and str(c).strip() != '':
                        hex_color = f"#{c}" if not str(c).startswith('#') else c
                
                if not hex_color:
                    hex_color = fallback_colors.get(team_name, '#262730')
                
                # Calculate text contrast
                try:
                    h = hex_color.lstrip('#')
                    rgb = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
                    lum = (0.299*rgb[0] + 0.587*rgb[1] + 0.114*rgb[2])
                    text_color = '#000000' if lum > 140 else '#ffffff'
                except:
                    text_color = '#ffffff'

                styles = []
                for col in row.index:
                    if col == 'FullName':
                        styles.append(f'background-color: {hex_color}; color: {text_color}; font-weight: bold;')
                    else:
                        styles.append('')
                return styles

            st.dataframe(results[cols].style.apply(style_rows, axis=1), hide_index=True, use_container_width=True)
            
        except Exception as e:
            st.error(f"Could not load results: {e}")

def show_news():
    """Fetch and display news from RSS."""
    
    # Countdown Header
    session_name, session_date = get_next_f1_session()
    
    c1, c2 = st.columns([3, 1])
    with c1:
        st.header("📰 Latest News & Results")
    with c2:
        if session_name and session_date:
            delta = session_date - datetime.datetime.now(datetime.timezone.utc)
            days = delta.days
            hours, rem = divmod(delta.seconds, 3600)
            mins, _ = divmod(rem, 60)
            st.metric(label=f"🔜 {session_name}", value=f"{days}d {hours}h {mins}m")
    
    # 1. Show Results Table First
    show_latest_results()
    
    st.divider()
    st.subheader("🗞️ Breaking News")
    
    # Check for library installation inside the function to prevent app crash
    try:
        import feedparser
    except ImportError:
        st.error("⚠️ Missing Dependency")
        st.info("To see the news, please run this command in your terminal:")
        st.code("pip install feedparser")
        return

    # RSS Feed URL (Official F1.com Feed)
    rss_url = "https://www.formula1.com/content/fom-website/en/latest/all.xml"
    
    try:
        feed = feedparser.parse(rss_url)
        
        if not feed.entries:
            st.warning("News feed currently unavailable. Please check back later.")
            return
            
        # Display the top 10 latest articles
        for entry in feed.entries[:10]:
            with st.container():
                st.subheader(entry.title)
                
                # Clean up summary text (remove HTML tags and "Keep reading" links)
                # Prefer 'content' (longer) over 'summary' (shorter) if available
                if 'content' in entry and len(entry.content) > 0:
                    summary_text = entry.content[0].value
                else:
                    summary_text = entry.get('summary', '')

                summary_text = summary_text.replace("<br />", "\n").replace("<br>", "\n")
                summary_text = re.sub(r'<a\s+class="more".*?>.*?</a>', '', summary_text, flags=re.IGNORECASE)
                summary_text = re.sub(r'<[^>]+>', '', summary_text)
                
                # Display summary text
                st.write(summary_text.strip())
                
                # Link to full article
                st.markdown(f"👉 [**Read Full Article**]({entry.link})")
                st.divider()
                
    except Exception as e:
        st.error(f"Could not load news: {e}")
