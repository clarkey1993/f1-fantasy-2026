import streamlit as st

def apply_custom_styles():
    st.markdown("""
        <style>
            .stApp { background-color: #0E1117; }
            header { visibility: hidden; }
            footer { visibility: hidden; }
            .main { background-color: #0E1117; }
            /* Make tabs easier to tap on mobile */
            .stTabs [data-baseweb="tab"] { font-size: 18px; font-weight: bold; }
        </style>
        """, unsafe_allow_html=True)