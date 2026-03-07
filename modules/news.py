import streamlit as st
import re

def show_news():
    """Fetch and display news from RSS."""
    st.header("📰 Latest Formula 1 News")
    
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
