#!/usr/bin/env python3
"""Watt & Where: synthetic dataset for the fictional apartment "Sunrise Heights" (Bengaluru).
Requires numpy and pandas only (plus the standard library). Python 3.10+."""
import json
import math
import os

import numpy as np
import pandas as pd

# ---------------- Placeholder tariff (NOT real BESCOM rates) ----------------
ENERGY_RATE = 9.00            # INR per kWh
FIXED_CHARGE = 5000.00        # INR per month
DEMAND_RATE_PER_KVA = 350.0   # INR per kVA
DEMAND_KVA_MEAN = 42.0
DEMAND_KVA_SD = 1.5
TAX_RATE = 0.09
SOLAR_CREDIT = 0.0

OUT_DIR = "data"
rng = np.random.default_rng(42)

# ---------------- Seasonal profiles (index 0 = January) ----------------
WATER = np.array([0.98, 1.00, 1.08, 1.12, 1.12, 1.00, 0.94, 0.94, 0.96, 0.98, 0.97, 0.97])
STP = 1 + 0.5 * (WATER - 1)
LIGHTING = np.array([1.05, 1.01, 0.97, 0.95, 0.95, 0.96, 0.98, 0.98, 0.99, 1.02, 1.04, 1.06])
FLAT = np.ones(12)
OTHER = np.array([1.0, 1.0, 1.15, 1.15, 1.15, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0])
PROFILE = {"water": WATER, "stp": STP, "lighting": LIGHTING, "flat": FLAT}

TRUE_FACTORS = {"pumps": 0.97, "lifts": 1.05, "stp": 1.02, "water_treatment": 0.98, "lighting": 1.00}

PERIODS = pd.period_range("2024-04", "2026-04", freq="M")
FAULT_MONTH = pd.Period("2026-03", freq="M")
DECOY_MONTH = pd.Period("2024-12", freq="M")
DECOY_EXTRA_KWH = 129.6
LOG_MONTHS = {pd.Period(m, freq="M") for m in ("2025-03", "2026-02", "2026-03", "2026-04")}

# ---------------- FILE 1: equipment inventory ----------------
INV_COLS = ["equipment_id", "equipment_type", "name", "location", "quantity", "rated_kw_per_unit",
            "rated_hp", "voltage", "expected_hours_per_day", "seasonal_profile", "installation_year",
            "amc_vendor", "control_type", "duty_status"]
N = None
INV_ROWS = [
    ["P1", "pump", "Borewell transfer pump 1", "Pump room", 1, 5.5, 7.5, 415, 4.0, "water", 2019, "Aqua Pumps & Services", "pressure_switch", "duty"],
    ["P2", "pump", "Borewell transfer pump 2", "Pump room", 1, 5.5, 7.5, 415, 0.0, "water", 2019, "Aqua Pumps & Services", "pressure_switch", "standby"],
    ["P3", "pump", "Domestic booster pump", "Pump room", 1, 3.7, 5.0, 415, 6.0, "water", 2021, "Aqua Pumps & Services", "pressure_switch", "duty"],
    ["LIFT", "lift", "Passenger lifts (4 units)", "Blocks A,B", 4, 7.5, 10.0, 415, 1.35, "flat", 2018, "LiftTech Elevators", "none", "duty"],
    ["STP_BLOWER", "stp", "STP aeration blower", "STP room", 1, 5.5, 7.5, 415, 16.0, "stp", 2020, "GreenFlow STP Services", "none", "duty"],
    ["STP_FEED", "stp", "STP feed pump", "STP room", 1, 1.5, 2.0, 415, 8.0, "stp", 2020, "GreenFlow STP Services", "none", "duty"],
    ["WTP", "water_treatment", "Softener/filter pump", "WTP room", 1, 2.2, 3.0, 415, 4.5, "water", 2020, "GreenFlow STP Services", "none", "duty"],
    ["LT_CORRIDOR", "lighting", "Corridor LED fixtures", "Corridors", 180, 0.012, N, 230, 12.0, "lighting", 2022, "BrightLine Electricals", "timer", "duty"],
    ["LT_STAIRS", "lighting", "Staircase LED fixtures", "Staircases", 90, 0.009, N, 230, 12.0, "lighting", 2022, "BrightLine Electricals", "manual", "duty"],
    ["LT_PARKING", "lighting", "Basement/parking fixtures", "Basement", 60, 0.018, N, 230, 12.0, "lighting", 2022, "BrightLine Electricals", "timer", "duty"],
    ["LT_LANDSCAPE", "lighting", "Landscape/pathway fixtures", "Grounds", 24, 0.020, N, 230, 11.0, "lighting", 2022, "BrightLine Electricals", "timer", "duty"],
]
inv = pd.DataFrame(INV_ROWS, columns=INV_COLS)

GROUP_OF = {"P1": "pumps", "P2": "pumps", "P3": "pumps", "LIFT": "lifts", "STP_BLOWER": "stp",
            "STP_FEED": "stp", "WTP": "water_treatment", "LT_CORRIDOR": "lighting",
            "LT_STAIRS": "lighting", "LT_PARKING": "lighting", "LT_LANDSCAPE": "lighting"}
inv["group"] = inv["equipment_id"].map(GROUP_OF)
inv["daily_nameplate_kwh"] = inv["rated_kw_per_unit"] * inv["expected_hours_per_day"] * inv["quantity"]
nameplate30 = (inv.groupby("group")["daily_nameplate_kwh"].sum() * 30).round(1).to_dict()
EXPECTED30 = {"pumps": 1326.0, "lifts": 1215.0, "stp": 3000.0, "water_treatment": 297.0, "lighting": 1616.4}
for g, v in EXPECTED30.items():  # sanity check of the spec's stated nameplate totals
    assert abs(nameplate30[g] - v) < 0.05, (g, nameplate30[g], v)
assert abs(sum(nameplate30.values()) - 7454.4) < 0.05
GROUP_DAILY = inv.groupby("group")["daily_nameplate_kwh"].sum().to_dict()
GROUP_PROFILE = {"lifts": "flat", "stp": "stp", "water_treatment": "water", "lighting": "lighting"}

# ---------------- Ground-truth simulation ----------------
truth_rows, bill_rows = [], []
daily_minutes = {}  # period -> (dates, p1_minutes, p3_minutes)

for per in PERIODS:
    days, m = per.days_in_month, per.month
    dates = pd.date_range(per.start_time, periods=days, freq="D")
    wp = WATER[m - 1]

    p1 = np.maximum(2.5, 4.0 * wp + rng.normal(0, 0.25, days))
    if per == FAULT_MONTH:
        p1 = p1 + 4.0
    p3 = np.maximum(3.0, 6.0 * wp + rng.normal(0, 0.3, days))
    # Daily run time is held to whole minutes so that the pump log sums to it exactly.
    p1_min = np.rint(p1 * 60).astype(int)
    p3_min = np.rint(p3 * 60).astype(int)
    daily_minutes[per] = (dates, p1_min, p3_min)
    pumps = (5.5 * p1_min.sum() / 60 + 3.7 * p3_min.sum() / 60) * TRUE_FACTORS["pumps"]

    cat = {"pumps": pumps}
    for g in ("lifts", "stp", "water_treatment", "lighting"):
        prof = PROFILE[GROUP_PROFILE[g]][m - 1]
        cat[g] = GROUP_DAILY[g] * days * prof * TRUE_FACTORS[g] * rng.normal(1, 0.02)
    if per == DECOY_MONTH:
        cat["lighting"] += DECOY_EXTRA_KWH
    cat["other"] = 650 * OTHER[m - 1] * rng.normal(1, 0.04)

    cat = {k: round(float(v), 2) for k, v in cat.items()}
    total = round(sum(cat.values()), 2)
    excess = round(5.5 * 4.0 * days * TRUE_FACTORS["pumps"], 2) if per == FAULT_MONTH else 0.0
    truth_rows.append({"month": str(per), "pumps_kwh": cat["pumps"], "lifts_kwh": cat["lifts"],
                       "stp_kwh": cat["stp"], "water_treatment_kwh": cat["water_treatment"],
                       "lighting_kwh": cat["lighting"], "other_kwh": cat["other"],
                       "total_kwh": total, "fault_excess_kwh": excess})

    units = int(math.floor(total + 0.5))
    kva = rng.normal(DEMAND_KVA_MEAN, DEMAND_KVA_SD)
    energy = round(units * ENERGY_RATE, 2)
    fixed = round(FIXED_CHARGE, 2)
    demand = round(kva * DEMAND_RATE_PER_KVA, 2)
    tax = round(TAX_RATE * (energy + fixed + demand), 2)
    solar = round(SOLAR_CREDIT, 2)
    bill_rows.append({"month": str(per), "billing_period_start": per.start_time.strftime("%Y-%m-%d"),
                      "billing_period_end": per.end_time.strftime("%Y-%m-%d"),
                      "total_units_kwh": units, "energy_charge": energy, "fixed_charge": fixed,
                      "demand_charge": demand, "electricity_tax": tax, "solar_credit": solar,
                      "total_amount": round(energy + fixed + demand + tax - solar, 2)})

truth_df = pd.DataFrame(truth_rows)
bills_df = pd.DataFrame(bill_rows)

# ---------------- FILE 3: pump log ----------------
def hhmm(minute):
    return f"{minute // 60:02d}:{minute % 60:02d}"


def split_minutes(total, n, lo, hi):
    w = rng.uniform(lo, hi, n)
    parts = np.floor(w / w.sum() * total).astype(int)
    parts[-1] += total - parts.sum()
    return [int(x) for x in parts]


def place_sequential(durations, windows):
    """Start of each cycle drawn in its window, pushed later if needed so cycles never overlap."""
    out, prev_end = [], -10**6
    for dur, (a, b) in zip(durations, windows):
        start = max(int(rng.integers(a, b + 1)), prev_end + 10)
        stop = start + dur
        assert stop <= 1430, "cycle too late in the day"
        out.append((start, stop))
        prev_end = stop
    return out


P1_NORMAL_WINDOWS = [(300, 480), (720, 840), (1020, 1200)]   # 05-08, 12-14, 17-20
P1_FAULT_WINDOWS = [(270, 360), (570, 660), (840, 930), (1110, 1200)]
STATUSES = ["STUCK_CLOSED", "CHATTERING", "OK"]
log_rows = []
for per in PERIODS:
    if per not in LOG_MONTHS:
        continue
    dates, p1_min, p3_min = daily_minutes[per]
    for d, t1, t3 in zip(dates, p1_min, p3_min):
        ds = d.strftime("%Y-%m-%d")
        t1, t3 = int(t1), int(t3)
        if per == FAULT_MONTH:
            n = int(np.clip(math.ceil(t1 / 150), 3, 4))
            durs = split_minutes(t1, n, 0.9, 1.1)
            for (s, e), in zip([(s, e) for s, e in place_sequential(durs, P1_FAULT_WINDOWS[:n])]):
                log_rows.append([ds, "P1", hhmm(s), hhmm(e), e - s, int(rng.integers(55, 76)), 100,
                                 str(rng.choice(STATUSES, p=[0.75, 0.20, 0.05]))])
        else:
            n = int(rng.integers(2, 4))
            idx = sorted(rng.choice(3, n, replace=False)) if n == 2 else [0, 1, 2]
            durs = split_minutes(t1, n, 0.75, 1.25)
            for s, e in place_sequential(durs, [P1_NORMAL_WINDOWS[i] for i in idx]):
                log_rows.append([ds, "P1", hhmm(s), hhmm(e), e - s, int(rng.integers(25, 41)),
                                 int(rng.integers(92, 101)), "OK"])
        # P3: about 4 cycles, each placed inside its own segment of the day so none can overlap
        n3 = int(rng.choice([3, 4, 5], p=[0.1, 0.8, 0.1]))
        durs3 = split_minutes(t3, n3, 0.8, 1.2)
        seg = (1410 - 300) // n3
        for i, dur in enumerate(durs3):
            lo = 300 + i * seg
            hi = max(lo, lo + seg - dur)
            s = int(rng.integers(lo, hi + 1))
            log_rows.append([ds, "P3", hhmm(s), hhmm(s + dur), dur, None, None, "OK"])

pump_log = pd.DataFrame(log_rows, columns=["date", "pump_id", "start_time", "stop_time", "runtime_min",
                                           "tank_level_start_pct", "tank_level_stop_pct",
                                           "pressure_switch_status"])
pump_log = pump_log.sort_values(["date", "pump_id", "start_time"], kind="stable").reset_index(drop=True)
pump_log["tank_level_start_pct"] = pump_log["tank_level_start_pct"].astype("Int64")
pump_log["tank_level_stop_pct"] = pump_log["tank_level_stop_pct"].astype("Int64")

# ---------------- FILE 4: DG log ----------------
dg_rows = []
for per in PERIODS:
    days = per.days_in_month
    lam = 2.5 if per.month in (6, 7, 8, 9) else 1.5
    events = [(per.start_time.strftime("%Y-%m-%d"), 0.5, "Monthly test run")]
    for _ in range(int(rng.poisson(lam))):
        day = int(rng.integers(1, days + 1))
        events.append((f"{per.year}-{per.month:02d}-{day:02d}", round(float(rng.uniform(0.5, 4.0)), 2),
                       str(rng.choice(["BESCOM power cut", "Planned BESCOM shutdown"]))))
    for date, hrs, reason in events:
        fuel = round(hrs * 18 * float(rng.uniform(0.9, 1.1)), 2)
        dg_rows.append([date, hrs, fuel, reason, 90.0, round(fuel * 90.0, 2)])
dg_df = pd.DataFrame(dg_rows, columns=["date", "run_hours", "fuel_litres", "reason",
                                       "diesel_price_inr_per_litre", "cost_inr"])
dg_df = dg_df.sort_values("date", kind="stable").reset_index(drop=True)

# ---------------- FILE 5: maintenance events ----------------
maint = pd.DataFrame([
    ["2024-09-10", "P3", "Routine AMC service", "Bearings greased, seal replaced", 3500],
    ["2024-12-17", "LT_CORRIDOR", "Corridor timers failed, lights on 24h", "Timers replaced", 1800],
    ["2025-02-18", "LIFT", "Door sensor fault on one lift", "Sensor replaced", 6200],
    ["2025-06-20", "STP_BLOWER", "Belt and bearing wear", "Belt and bearing replaced", 9800],
    ["2025-09-03", "P1", "Routine AMC service", "Pressure switch checked, found OK", 2500],
    ["2026-03-31", "P1", "Residents report pump room running at night", "Logged for inspection", 0],
    ["2026-04-01", "P1", "Pressure switch stuck closed, pump running", "Pressure switch and relay replaced", 7400],
], columns=["date", "equipment_id", "issue", "action_taken", "cost_inr"])
maint.insert(0, "event_id", [f"M{i:03d}" for i in range(1, len(maint) + 1)])

# ---------------- Write files ----------------
os.makedirs(OUT_DIR, exist_ok=True)
inv[INV_COLS].to_csv(f"{OUT_DIR}/equipment_inventory.csv", index=False)
bills_df.to_csv(f"{OUT_DIR}/bills.csv", index=False)
pump_log.to_csv(f"{OUT_DIR}/pump_log.csv", index=False)
dg_df.to_csv(f"{OUT_DIR}/dg_log.csv", index=False)
maint.to_csv(f"{OUT_DIR}/maintenance_events.csv", index=False)
truth_df.to_csv(f"{OUT_DIR}/monthly_truth.csv", index=False)
with open(f"{OUT_DIR}/tariff_scenarios.json", "w") as fh:
    json.dump({"stp_residential_common_rate": 8.0, "stp_commercial_rate": 11.0,
               "note": "placeholder rates, replace with actual BESCOM tariff-order values"}, fh)

# ---------------- Acceptance checks (re-read from disk) ----------------
def report(n, ok, detail):
    print(f"Check {n}: {'PASS' if ok else 'FAIL'}  {detail}")


b = pd.read_csv(f"{OUT_DIR}/bills.csv").set_index("month")
t = pd.read_csv(f"{OUT_DIR}/monthly_truth.csv").set_index("month")
pl = pd.read_csv(f"{OUT_DIR}/pump_log.csv")
u = b["total_units_kwh"]

ok = (len(b) == 25 and b.index[0] == "2024-04" and b.index[-1] == "2026-04"
      and (u == np.floor(t["total_kwh"] + 0.5).astype(int)).all())
report(1, ok, f"{len(b)} rows, {b.index[0]} to {b.index[-1]}, units match truth")

r2 = u["2026-03"] / u["2025-03"] - 1
report(2, 0.06 <= r2 <= 0.095, f"2026-03 vs 2025-03 = {r2:+.2%}")

r3 = u["2026-04"] / u["2025-04"] - 1
report(3, abs(r3) <= 0.04, f"2026-04 vs 2025-04 = {r3:+.2%}")

others = u.drop("2026-03")
dec = t.loc["2024-12", "total_kwh"]
dec_pct = dec / (dec - DECOY_EXTRA_KWH) - 1
report(4, others.between(7500, 9000).all() and 0.012 <= dec_pct <= 0.018,
       f"non-fault range {others.min()}-{others.max()}, 2024-12 decoy = {dec_pct:+.2%}")

fx = t.loc["2026-03", "fault_excess_kwh"]
nz = (t["fault_excess_kwh"] != 0).sum()
report(5, 640 <= fx <= 680 and nz == 1, f"fault_excess 2026-03 = {fx} kWh (nonzero months: {nz})")

p1 = pl[pl.pump_id == "P1"]
rt = lambda mth: p1[p1.date.str.startswith(mth)]["runtime_min"].sum()
ratio = rt("2026-03") / rt("2025-03")
report(6, 1.85 <= ratio <= 2.1, f"P1 runtime ratio = {ratio:.3f} ({rt('2026-03')} / {rt('2025-03')} min)")

def to_min(s):
    h, mm = s.split(":")
    return int(h) * 60 + int(mm)

s_, e_ = pl.start_time.map(to_min), pl.stop_time.map(to_min)
dur_ok = ((e_ - s_) == pl.runtime_min).all()
mid_ok = ((e_ <= 1438) & (e_ > s_)).all()
tmp = pl.assign(s=s_, e=e_).sort_values(["date", "pump_id", "s"])
prev_e = tmp.groupby(["date", "pump_id"])["e"].shift()
overlap_ok = (prev_e.isna() | (tmp["s"] >= prev_e)).all()
day_sums = pl.groupby(["date", "pump_id"])["runtime_min"].sum()
sum_ok = True
for per in PERIODS:
    if per in LOG_MONTHS:
        dts, a, c = daily_minutes[per]
        for d, x, y in zip(dts, a, c):
            ds = d.strftime("%Y-%m-%d")
            sum_ok &= day_sums[(ds, "P1")] == x and day_sums[(ds, "P3")] == y
report(7, bool(dur_ok and mid_ok and overlap_ok and sum_ok),
       f"runtime=stop-start {dur_ok}, before midnight {mid_ok}, no overlap {overlap_ok}, daily sums match sim {sum_ok}")

expected_files = {"equipment_inventory.csv", "bills.csv", "pump_log.csv", "dg_log.csv",
                  "maintenance_events.csv", "monthly_truth.csv", "tariff_scenarios.json"}
found = set(os.listdir(OUT_DIR))
report(8, found == expected_files, f"{len(found)} files in ./{OUT_DIR}/")