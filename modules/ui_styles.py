import streamlit as st

def apply_custom_styles():
    st.markdown("""
        <style>
            /* 1. HEADERS (F1 Red) */
            h1, h2, h3 {
                color: #e10600 !important;
                font-weight: 800;
            }
            
            /* 2. SIDEBAR STYLING */
            [data-testid="stSidebar"] {
                background-color: #15151e;
                border-right: 1px solid #333;
            }
            /* Force white text in sidebar for readability */
            [data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label {
                color: #ffffff !important;
            }
            
            /* 3. METRIC CARDS (Stats) */
            [data-testid="stMetric"] {
                background-color: #262730;
                padding: 15px;
                border-radius: 8px;
                border-left: 5px solid #e10600; /* Red Accent */
                box-shadow: 0 4px 6px rgba(0,0,0,0.3);
            }
            /* Force text color inside metrics to be readable on dark background */
            [data-testid="stMetricLabel"] {
                color: #e0e0e0 !important;
            }
            [data-testid="stMetricValue"] {
                color: #ffffff !important;
            }
            
            /* 4. BUTTONS */
            .stButton > button {
                background-color: #e10600;
                color: white;
                border-radius: 6px;
                border: none;
                font-weight: bold;
                transition: all 0.2s ease;
            }
            .stButton > button:hover {
                background-color: #b30000;
                transform: scale(1.02);
            }

            /* 5. SIDEBAR HOME BUTTON (Transparent) */
            [data-testid="stSidebar"] .stButton > button {
                background-color: transparent;
                color: #ffffff;
                border: none;
                font-size: 22px;
                font-weight: 800;
                text-align: left;
                justify-content: flex-start;
                padding-left: 0;
            }
            [data-testid="stSidebar"] .stButton > button:hover {
                background-color: transparent;
                color: #e10600;
                transform: none;
            }

            /* 6. UTILS */
            footer { visibility: hidden; }
        </style>
        """, unsafe_allow_html=True)