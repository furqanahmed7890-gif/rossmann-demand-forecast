import streamlit as st

st.title("About This Project")

st.markdown(r"""
Forecasting plus optimization, end to end: predict the next 6 weeks of sales and customer traffic for every
Rossmann drugstore, then turn the forecast into the cheapest staffing plan that still covers every day.

### The data
The [Rossmann Store Sales](https://www.kaggle.com/competitions/rossmann-store-sales) dataset: 1,017,209 days of
sales and customer counts for 1,115 real drugstores across Germany (January 2013 to July 2015), with
promotions, school and public holidays, store type, assortment, and nearest competitor.

### How it was built
1. **Explore.** Promotions lift sales 39% (21% more customers, each spending 15% more). Stores close on
   Sundays. 180 stores are missing six months of data.
2. **Backtest honestly.** The last 6 weeks of history were held out, the model trained only on earlier data,
   and early stopping used a separate validation window, so the test was never touched.
3. **Beat real baselines.** LightGBM on log sales vs. each store's recent weekday average and its weekday x
   promo average.
4. **Forecast the future window** (Aug 1 to Sep 17, 2015) for 856 stores, using the promotion calendar the
   company had already planned.
5. **Optimize.** Forecast customers become daily staff requirements; an integer program chooses full-time
   day-off patterns and part-time shifts at the lowest wage cost (72 whole-number decisions).
6. **Excel Solver.** The same model as a spreadsheet with live formulas. Run from an empty plan, Excel
   Solver reaches exactly the same optimum as Python.

### Results
| | |
|---|---|
| Sales forecast error (WAPE), 6-week backtest | **8.7%** (baseline 9.8%, naive 18.1%) |
| Customer forecast error (WAPE) | **6.8%** (baseline 8.6%) |
| Forecast bias | +0.1% |
| Store 929 staffing, 6 weeks | **30,960 EUR** vs. 42,048 EUR flat (**26.4% saved**) |
| All 829 Sunday-closed stores | **8.26M EUR saved** over 6 weeks (24.1%) |

### Limitations
- The wage costs, customers served per employee, and minimum crew are illustrative assumptions, not
  Rossmann's real figures. The app lets you change them and re-solve.
- Staffing is planned per day, not per hour, and treats every employee as interchangeable.
- The forecast assumes the promotion calendar is known in advance and that nothing unusual (refits,
  closures) happens to a store.
- The savings compare against a simple flat plan; a real store manager already does better than that.

### Tech stack
Python, pandas, LightGBM, SciPy (`milp`), Excel Solver (Simplex LP), openpyxl, Streamlit, Altair

### Source code
[github.com/furqanahmed7890-gif/rossmann-demand-forecast](https://github.com/furqanahmed7890-gif/rossmann-demand-forecast)
""")
