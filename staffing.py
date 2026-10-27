"""Staffing plan: cover forecast customer traffic at the lowest wage cost.

Shared by notebook 03 and the app. The same model is built in Excel for Solver (staffing_plan.xlsx).

Decisions, for each of the planning weeks (Mon-Sat; the stores close on Sundays):
  full_time[w, p]  full-time employees in week w whose day off is day p (they work the other 5 days)
  part_time[w, d]  part-time shifts booked on day d of week w
Constraint: staff on duty each day >= staff required by the forecast.
Objective: minimize total wage cost. All decisions are whole numbers.
"""
import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

DEFAULTS = dict(
    customers_per_staff=120,     # customers one employee can serve in an 8-hour shift
    safety_buffer=0.10,          # extra cover for forecast error
    min_staff=3,                 # minimum on duty whenever the store is open
    full_time_weekly_cost=640,   # 5 shifts x 8 hours x 16 EUR
    part_time_shift_cost=152,    # 8 hours x 19 EUR: flexible, so pricier per hour
)


def required_staff(customers, is_open, customers_per_staff, safety_buffer, min_staff):
    need = np.ceil(np.asarray(customers) * (1 + safety_buffer) / customers_per_staff)
    return np.where(np.asarray(is_open) == 1, np.maximum(need, min_staff), 0).astype(int)


def solve_plan(required, full_time_weekly_cost, part_time_shift_cost):
    required = np.asarray(required)
    weeks = required.shape[0]
    n = weeks * 6
    cost = np.concatenate([np.full(n, float(full_time_weekly_cost)), np.full(n, float(part_time_shift_cost))])

    coverage = np.zeros((n, 2 * n))
    for w in range(weeks):
        for d in range(6):
            row = w * 6 + d
            coverage[row, w * 6:(w + 1) * 6] = 1   # every full-timer in week w...
            coverage[row, w * 6 + d] = 0           # ...except those whose day off is d
            coverage[row, n + row] = 1             # plus part-time shifts that day

    result = milp(
        cost,
        constraints=LinearConstraint(coverage, lb=required.ravel(), ub=np.inf),
        integrality=np.ones(2 * n),
        bounds=Bounds(0, np.inf),
    )
    if result.status != 0:
        raise RuntimeError(result.message)
    full_time = np.round(result.x[:n]).reshape(weeks, 6).astype(int)
    part_time = np.round(result.x[n:]).reshape(weeks, 6).astype(int)
    on_duty = full_time.sum(axis=1, keepdims=True) - full_time + part_time
    return {
        "full_time": full_time,
        "part_time": part_time,
        "on_duty": on_duty,
        "full_time_cost": float(full_time.sum() * full_time_weekly_cost),
        "part_time_cost": float(part_time.sum() * part_time_shift_cost),
        "cost": float(result.fun),
    }


def flat_requirement(required):
    """What a manager without a daily forecast does: staff every open day for the busiest day."""
    required = np.asarray(required)
    return np.where(required > 0, required.max(), 0)
