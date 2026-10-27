import altair as alt
import pandas as pd
import streamlit as st

from data_access import load, store_picker

FEATURED = 929

st.title("6-Week Sales Forecast for 1,115 Rossmann Stores")
st.write(
    "A LightGBM model trained on 2.5 years of daily sales. It was tested on the last 6 weeks of history, which "
    "it never saw during training, then retrained and used to forecast August 1 to September 17, 2015, with the "
    "promotion calendar the company had already planned."
)

metrics = load("metrics")
model = metrics[metrics["method"] == "LightGBM"].set_index("target")
baseline = metrics[metrics["method"] == "Weekday x promo average"].set_index("target")
cols = st.columns(4)
cols[0].metric("Sales error (WAPE)", f"{model.loc['Sales', 'WAPE']:.1%}",
               delta=f"{model.loc['Sales', 'WAPE'] - baseline.loc['Sales', 'WAPE']:.1%} vs. baseline", delta_color="inverse")
cols[1].metric("Customer error (WAPE)", f"{model.loc['Customers', 'WAPE']:.1%}",
               delta=f"{model.loc['Customers', 'WAPE'] - baseline.loc['Customers', 'WAPE']:.1%} vs. baseline",
               delta_color="inverse")
cols[2].metric("Forecast bias, sales", f"{model.loc['Sales', 'bias']:+.1%}", help="Positive = over-forecast")
cols[3].metric("RMSPE (Kaggle metric)", f"{model.loc['Sales', 'RMSPE']:.3f}")

forecast = load("forecast_future")
backtest = load("backtest")
history = load("history")
accuracy = load("store_accuracy").set_index("Store")

store = store_picker(forecast["Store"].unique(), FEATURED, key="forecast_store")
target = st.radio("Show", ["Sales", "Customers"], horizontal=True)
forecast_col = f"forecast_{target.lower()}"

past = history[(history["Store"] == store) & (history["Date"] < backtest["Date"].min())]
test = backtest[backtest["Store"] == store]
future = forecast[(forecast["Store"] == store) & (forecast["Open"] == 1)]

series = pd.concat([
    pd.DataFrame({"Date": past["Date"], "value": past[target], "series": "Actual", "Promo": past["Promo"]}),
    pd.DataFrame({"Date": test["Date"], "value": test[target], "series": "Actual", "Promo": test["Promo"]}),
    pd.DataFrame({"Date": test["Date"], "value": test[f"{target}_model"], "series": "Backtest prediction",
                  "Promo": test["Promo"]}),
    pd.DataFrame({"Date": future["Date"], "value": future[forecast_col], "series": "Forecast", "Promo": future["Promo"]}),
])
colors = alt.Scale(domain=["Actual", "Backtest prediction", "Forecast"], range=["#9e9e9e", "#4682b4", "#ff8c00"])
lines = alt.Chart(series).mark_line(point=alt.OverlayMarkDef(size=18)).encode(
    x=alt.X("Date:T", title=None),
    y=alt.Y("value:Q", title=f"Daily {target.lower()}"),
    color=alt.Color("series:N", scale=colors, title=None),
    tooltip=[alt.Tooltip("Date:T", format="%a %d %b %Y"), "series", alt.Tooltip("value:Q", format=",.0f"), "Promo"],
)
split = alt.Chart(pd.DataFrame({"Date": [backtest["Date"].min(), forecast["Date"].min()]})).mark_rule(
    color="gray", strokeDash=[4, 4]).encode(x="Date:T")
st.altair_chart(lines + split, width="stretch")
st.caption("Dashed lines: start of the 6-week backtest, and start of the real forecast. Sundays are closed.")

if store in accuracy.index:
    row = accuracy.loc[store]
    st.write(
        f"**Store {store} backtest:** sales error {row['sales_wape']:.1%}, customer error {row['customers_wape']:.1%} "
        f"(median store: {accuracy['sales_wape'].median():.1%} and {accuracy['customers_wape'].median():.1%})."
    )

left, right = st.columns(2)
with left:
    st.subheader("Model vs. baselines (backtest)")
    st.dataframe(metrics, hide_index=True, width="stretch",
                 column_config={c: st.column_config.NumberColumn(format="%.3f") for c in ["WAPE", "RMSPE", "bias"]})
    st.caption("WAPE = total absolute error / total actual. Baselines: each store's recent weekday average, and its "
               "weekday average split by promo vs. no promo over the last year.")
with right:
    st.subheader("What the model relies on")
    importance = load("feature_importance")
    chart = alt.Chart(importance).mark_bar(color="#4682b4").encode(
        x=alt.X("gain_share:Q", title="Share of total gain", axis=alt.Axis(format="%")),
        y=alt.Y("feature:N", sort="-x", title=None),
    )
    st.altair_chart(chart, width="stretch")
