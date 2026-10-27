from pathlib import Path

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from data_access import load, store_picker
from staffing import DAYS, DEFAULTS, flat_requirement, required_staff, solve_plan

FEATURED = 929
START, END = pd.Timestamp("2015-08-03"), pd.Timestamp("2015-09-12")
WORKBOOK = Path(__file__).parent / "excel" / "staffing_plan.xlsx"

st.title("Forecast-Driven Staffing Plan")
st.write(
    "Turns a store's 6-week customer forecast into the cheapest staffing plan that covers every day: how many "
    "full-time employees (each works 5 of the 6 days) and how many part-time shifts. Solved as an integer program "
    "right now, in your browser. The same model ships as an Excel Solver workbook."
)

forecast = load("forecast_future")
window = forecast[(forecast["Date"] >= START) & (forecast["Date"] <= END)]
sunday_open = window[window["DayOfWeek"] == 7].groupby("Store")["Open"].max()
eligible = sunday_open[sunday_open == 0].index

with st.sidebar:
    st.header("Assumptions")
    customers_per_staff = st.slider("Customers one employee serves per shift", 80, 200, DEFAULTS["customers_per_staff"], 10)
    safety_buffer = st.slider("Safety buffer for forecast error", 0, 30, int(DEFAULTS["safety_buffer"] * 100), 5,
                              format="%d%%") / 100
    min_staff = st.slider("Minimum crew when open", 1, 6, DEFAULTS["min_staff"])
    full_time_cost = st.number_input("Full-time cost per week (EUR)", 300, 1500, DEFAULTS["full_time_weekly_cost"], 10)
    part_time_cost = st.number_input("Part-time cost per shift (EUR)", 60, 400, DEFAULTS["part_time_shift_cost"], 2)

store = store_picker(eligible, FEATURED, key="staffing_store")
rows = window[(window["Store"] == store) & (window["DayOfWeek"] < 7)].sort_values("Date")
customers = rows["forecast_customers"].to_numpy().reshape(6, 6)
is_open = rows["Open"].to_numpy().reshape(6, 6)
promo = rows["Promo"].to_numpy().reshape(6, 6)
weeks = [f"Week of {d:%d %b}" for d in rows["Date"].iloc[::6]]

required = required_staff(customers, is_open, customers_per_staff, safety_buffer, min_staff)
plan = solve_plan(required, full_time_cost, part_time_cost)
flat = solve_plan(flat_requirement(required), full_time_cost, part_time_cost)

cols = st.columns(4)
cols[0].metric("Optimized 6-week labor cost", f"{plan['cost']:,.0f} EUR")
cols[1].metric("Flat staffing at the peak", f"{flat['cost']:,.0f} EUR")
cols[2].metric("Saved", f"{flat['cost'] - plan['cost']:,.0f} EUR",
               delta=f"{1 - plan['cost'] / flat['cost']:.1%}" if flat["cost"] else None)
cols[3].metric("Full-time weeks / part-time shifts", f"{plan['full_time'].sum()} / {plan['part_time'].sum()}")

daily = rows[["Date"]].copy()
daily["day_label"] = daily["Date"].dt.strftime("%a %d %b")
daily["required"] = required.ravel()
daily["optimized"] = plan["on_duty"].ravel()
daily["flat"] = flat["on_duty"].ravel()
daily["day"] = np.where(promo.ravel() == 1, "Promo day", "Regular day")
x = alt.X("day_label:N", sort=daily["day_label"].tolist(), title=None, axis=alt.Axis(labelAngle=-60))
bars = alt.Chart(daily).mark_bar(opacity=0.7).encode(
    x=x,
    y=alt.Y("required:Q", title="Staff"),
    color=alt.Color("day:N", scale=alt.Scale(domain=["Regular day", "Promo day"], range=["#4682b4", "#ff8c00"]),
                    title=None, legend=alt.Legend(orient="top")),
    tooltip=["day_label", "required", "optimized", "flat", "day"],
)
on_duty = alt.Chart(daily).mark_line(color="#2ca02c", strokeWidth=2.5, point=True).encode(x=x, y="optimized:Q")
flat_line = alt.Chart(daily).mark_line(color="gray", strokeDash=[4, 4]).encode(x=x, y="flat:Q")
st.altair_chart(bars + on_duty + flat_line, width="stretch")
st.caption("Bars: staff required by the forecast. Green line: on duty in the optimized plan. Dashed gray: a flat "
           "plan that staffs every day for the busiest day.")

left, right = st.columns(2)
left.markdown("**Full-time employees by day off** (each works the other 5 days)")
left.dataframe(pd.DataFrame(plan["full_time"], index=weeks, columns=[f"off {d}" for d in DAYS]), width="stretch")
right.markdown("**Part-time shifts booked**")
right.dataframe(pd.DataFrame(plan["part_time"], index=weeks, columns=DAYS), width="stretch")

with st.expander("Forecast customers and staff required, day by day"):
    st.dataframe(pd.concat({
        "forecast customers": pd.DataFrame(np.round(customers).astype(int), index=weeks, columns=DAYS),
        "staff required": pd.DataFrame(required, index=weeks, columns=DAYS),
    }, axis=1), width="stretch")

with st.expander("The optimization model"):
    st.markdown(r"""
- **Decisions** (whole numbers): full-timers per week and day-off pattern (36), part-time shifts per day (36).
- **Constraint:** for every day, full-timers working that day + part-time shifts $\ge$ staff required.
- **Staff required** = forecast customers $\times$ (1 + buffer) / customers per employee, rounded up, at least
  the minimum crew.
- **Objective:** minimize full-time weeks $\times$ weekly cost + part-time shifts $\times$ shift cost.
- Solved with `scipy.optimize.milp` here; the Excel version uses Solver's Simplex LP with integer constraints
  and reaches the same optimum.
""")

if WORKBOOK.exists():
    st.download_button(
        f"Download the Excel Solver workbook (store {FEATURED}, default assumptions)",
        WORKBOOK.read_bytes(),
        file_name="staffing_plan.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

st.subheader("Every store")
all_stores = load("staffing_all_stores")
cols = st.columns(3)
cols[0].metric("Stores planned", f"{len(all_stores):,}")
cols[1].metric("Saved over 6 weeks", f"{all_stores['savings'].sum() / 1e6:.2f}M EUR")
cols[2].metric("Median store saving", f"{all_stores['savings_pct'].median():.1%}")
histogram = alt.Chart(all_stores).mark_bar(color="#4682b4").encode(
    x=alt.X("savings_pct:Q", bin=alt.Bin(maxbins=30), title="Labor cost saved vs. flat staffing",
            axis=alt.Axis(format="%")),
    y=alt.Y("count():Q", title="Stores"),
)
st.altair_chart(histogram, width="stretch")
st.caption("Computed with the default assumptions in notebook 03.")
