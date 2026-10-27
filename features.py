"""Calendar and store features for the Rossmann forecast. Shared by the notebooks."""
import numpy as np
import pandas as pd

MONTH_ABBR = {1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
              7: "Jul", 8: "Aug", 9: "Sept", 10: "Oct", 11: "Nov", 12: "Dec"}

FEATURES = [
    "Store", "DayOfWeek", "Promo", "state_holiday", "SchoolHoliday",
    "store_type", "assortment", "competition_distance", "competition_open_months",
    "promo2_active", "year", "month", "day", "week_of_year", "day_of_year",
]


def add_features(days, stores):
    d = days.merge(stores, on="Store", how="left")
    date = d["Date"]
    d["year"] = date.dt.year
    d["month"] = date.dt.month
    d["day"] = date.dt.day
    d["week_of_year"] = date.dt.isocalendar().week.astype(int).to_numpy()
    d["day_of_year"] = date.dt.dayofyear
    d["state_holiday"] = d["StateHoliday"].astype(str).map({"0": 0, "a": 1, "b": 2, "c": 3}).fillna(0).astype(int)
    d["store_type"] = d["StoreType"].map({"a": 0, "b": 1, "c": 2, "d": 3})
    d["assortment"] = d["Assortment"].map({"a": 0, "b": 1, "c": 2})
    d["competition_distance"] = d["CompetitionDistance"]

    opened_months = ((d["year"] - d["CompetitionOpenSinceYear"]) * 12
                     + (d["month"] - d["CompetitionOpenSinceMonth"]))
    d["competition_open_months"] = opened_months.clip(lower=0)

    started = (d["year"] > d["Promo2SinceYear"]) | (
        (d["year"] == d["Promo2SinceYear"]) & (d["week_of_year"] >= d["Promo2SinceWeek"])
    )
    in_interval = [
        isinstance(interval, str) and MONTH_ABBR[month] in interval.split(",")
        for interval, month in zip(d["PromoInterval"], d["month"])
    ]
    d["promo2_active"] = ((d["Promo2"] == 1) & started & np.array(in_interval)).astype(int)

    # same category list everywhere, so LightGBM sees identical store codes in training and forecasting
    d["Store"] = pd.Categorical(d["Store"], categories=sorted(stores["Store"]))
    return d


def wape(actual, predicted):
    return np.abs(actual - predicted).sum() / actual.sum()


def rmspe(actual, predicted):
    return np.sqrt(np.mean(((actual - predicted) / actual) ** 2))


def bias(actual, predicted):
    return (predicted.sum() - actual.sum()) / actual.sum()
