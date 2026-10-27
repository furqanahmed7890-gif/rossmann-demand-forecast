import streamlit as st

st.set_page_config(page_title="Rossmann Forecast & Staffing", page_icon="🏪", layout="wide")

page = st.navigation([
    st.Page("forecast_page.py", title="Sales Forecast", icon="📈"),
    st.Page("staffing_page.py", title="Staffing Plan", icon="🧑‍🤝‍🧑"),
    st.Page("about.py", title="About", icon="ℹ️"),
])

page.run()
