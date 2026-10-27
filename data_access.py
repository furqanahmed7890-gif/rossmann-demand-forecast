from pathlib import Path

import pandas as pd
import streamlit as st

APP_DATA = Path(__file__).parent / "app_data"


@st.cache_data
def load(name):
    df = pd.read_csv(APP_DATA / f"{name}.csv")
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"])
    return df


def store_picker(stores, default, key):
    stores = sorted(int(s) for s in stores)
    return st.selectbox("Store", stores, index=stores.index(default) if default in stores else 0, key=key)
