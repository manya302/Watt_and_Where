"""Watt & Where analysis engine.

Pure local code (numpy and pandas only): no network, no AWS imports, no LLM calls.
The engine never reads monthly_truth.csv. Same input gives identical output JSON.
"""
from __future__ import annotations

import calendar
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

# --------------------------------------------------------------------------------------
# All thresholds live here.
# --------------------------------------------------------------------------------------
THRESHOLDS = {
    # Anomaly flagging (from the spec)
    "z_alert": 3.0,
    "z_watch_no_yoy": 3.5,
    "yoy_alert_pct": 5.0,
    "sd_floor_pp": 0.75,
    "rolling_window": 6,
    "min_history": 4,
    # Reconciliation confidence labels
    "confidence_high_abs_pct": 10.0,
    "confidence_medium_abs_pct": 20.0,
    # Pump attribution
    "pump_abnormal_ratio": 1.3,
    "pump_abnormal_delta_h_per_day": 1.5,
    "switch_not_ok_share": 0.5,
    "tank_start_rise_points": 15.0,
    "coverage_most_low": 0.7,
    "coverage_most_high": 1.3,
    # Success criteria for the next-month comparison
    "success_p1_hours_tolerance_pct": 10.0,
    "success_yoy_band_pct": 5.0,
}

# --------------------------------------------------------------------------------------
# All assumptions live here. Season multipliers are deliberately coarse and user-adjustable.
# Lists run January to December.
# --------------------------------------------------------------------------------------
ASSUMPTIONS = {
    "season_multipliers_label": (
        "Assumption: coarse, user-adjustable seasonal multipliers (not measured values). "
        "They are intentionally imperfect, so the reconciliation gap is realistic."
    ),
    "season_multipliers_jan_to_dec": {
        "pump": [1.00, 1.00, 1.10, 1.10, 1.10, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00],
        "water_treatment": [1.00, 1.00, 1.10, 1.10, 1.10, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00],
        "stp": [1.00, 1.00, 1.05, 1.05, 1.05, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00],
        "lift": [1.00] * 12,
        "lighting": [1.04, 1.04, 0.96, 0.96, 0.96, 0.96, 1.00, 1.00, 1.00, 1.00, 1.04, 1.04],
    },
    "lighting_manual_saving_fraction": 0.40,
    "lighting_manual_saving_label": "illustrative, validate with a sub-meter",
    "rolling_sd_ddof": 1,
    "estimate_uses_nameplate_only": "No true-factor is applied; unmetered load is not estimated.",
}

CATEGORIES = ["pump", "lift", "stp", "water_treatment", "lighting"]
SYNTHETIC_NOTE = "All input data is synthetic (fictional apartment, generated for a hackathon demo)."
INSUFFICIENT_EVIDENCE_MSG = "insufficient evidence: add runtime logging or a pump sub-meter"
HYP_RANK = {"high": 0, "medium": 1, "low": 2}


# --------------------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------------------
def _days(month: str) -> int:
    return calendar.monthrange(int(month[:4]), int(month[5:7]))[1]


def _shift_year(month: str, years: int) -> str:
    return f"{int(month[:4]) + years:04d}-{month[5:7]}"


def _prev_month(month: str) -> str:
    y, m = int(month[:4]), int(month[5:7])
    return f"{y - 1:04d}-12" if m == 1 else f"{y:04d}-{m - 1:02d}"


def _r(x, nd):
    """Round to nd decimals; None and NaN become None."""
    if x is None:
        return None
    x = float(x)
    if math.isnan(x) or math.isinf(x):
        return None
    return round(x, nd)


def _i(x):
    """Round to an integer; None and NaN become None."""
    v = _r(x, 6)
    return None if v is None else int(round(v))


def _f(x, nd=1):
    return "n/a" if x is None else f"{x:.{nd}f}"


def _season(category: str, month_number: int) -> float:
    return ASSUMPTIONS["season_multipliers_jan_to_dec"][category][month_number - 1]


def marginal_inr_per_kwh(bill: dict) -> float:
    """(energy / units) * (1 + tax_pct), tax_pct derived from the bill itself."""
    base = bill["energy_charge"] + bill["fixed_charge"] + bill["demand_charge"]
    tax_pct = bill["electricity_tax"] / base
    return bill["energy_charge"] / bill["total_units_kwh"] * (1.0 + tax_pct)


# --------------------------------------------------------------------------------------
# Loading (monthly_truth.csv is never read)
# --------------------------------------------------------------------------------------
def load_data(data_dir) -> dict:
    d = Path(data_dir)
    bills = pd.read_csv(d / "bills.csv", dtype={"month": str})
    inventory = pd.read_csv(d / "equipment_inventory.csv")
    dg_log = pd.read_csv(d / "dg_log.csv")
    with open(d / "tariff_scenarios.json", encoding="utf-8") as fh:
        tariff = json.load(fh)
    pl_path = d / "pump_log.csv"
    if pl_path.exists():
        pump_log = pd.read_csv(pl_path)
    else:
        pump_log = pd.DataFrame(columns=["date", "pump_id", "start_time", "stop_time", "runtime_min",
                                         "tank_level_start_pct", "tank_level_stop_pct",
                                         "pressure_switch_status"])
    return {"bills": bills, "inventory": inventory, "pump_log": pump_log, "dg_log": dg_log, "tariff": tariff}


# --------------------------------------------------------------------------------------
# Step 1: estimate
# --------------------------------------------------------------------------------------
def estimate_month(inventory_rows: list, month: str) -> dict:
    days, mnum = _days(month), int(month[5:7])
    out = {c: 0.0 for c in CATEGORIES}
    for row in inventory_rows:
        cat = row["equipment_type"]
        if cat not in out:
            raise ValueError(f"unknown equipment_type: {cat}")
        out[cat] += (float(row["rated_kw_per_unit"]) * float(row["quantity"])
                     * float(row["expected_hours_per_day"]) * days * _season(cat, mnum))
    return out


def estimate_row_kwh(row: dict, month: str) -> float:
    return (float(row["rated_kw_per_unit"]) * float(row["quantity"]) * float(row["expected_hours_per_day"])
            * _days(month) * _season(row["equipment_type"], int(month[5:7])))


def confidence_label(unexplained_pct: float) -> str:
    a = abs(unexplained_pct)
    if a <= THRESHOLDS["confidence_high_abs_pct"]:
        return "High"
    if a <= THRESHOLDS["confidence_medium_abs_pct"]:
        return "Medium"
    return "Low"


# --------------------------------------------------------------------------------------
# Step 3: anomaly flags
# --------------------------------------------------------------------------------------
def flag_months(months: list) -> None:
    """Adds yoy_pct, rolling_z, status, reasons to each month dict (in place)."""
    T = THRESHOLDS
    by_month = {m["month"]: m for m in months}
    pcts = [m["unexplained_pct"] for m in months]
    for i, m in enumerate(months):
        prev = pcts[max(0, i - T["rolling_window"]):i]
        z = mean = sd = None
        if len(prev) >= T["min_history"]:
            mean = float(np.mean(prev))
            sd = float(np.std(prev, ddof=ASSUMPTIONS["rolling_sd_ddof"]))
            z = (pcts[i] - mean) / max(sd, T["sd_floor_pp"])
        ref = by_month.get(_shift_year(m["month"], -1))
        yoy = None
        if ref is not None:
            yoy = (m["actual_units"] - ref["actual_units"]) / ref["actual_units"] * 100.0
        m["_mean"], m["_sd"] = mean, sd
        m["rolling_z"], m["yoy_pct"] = z, yoy

        if z is None:
            m["status"] = "normal"
            m["reasons"] = [f"insufficient history: {len(prev)} prior months available, need {T['min_history']}"]
            continue

        z_hi = z >= T["z_alert"]
        if yoy is not None:
            yoy_hi = yoy >= T["yoy_alert_pct"]
            if yoy_hi and z_hi:
                status = "alert"
            elif z_hi or yoy_hi:
                status = "watch"
            else:
                status = "normal"
        else:
            status = "watch" if z >= T["z_watch_no_yoy"] else "normal"
        m["status"] = status

        reasons = [
            f"Unexplained share is {pcts[i]:.1f}% of billed units; the previous {len(prev)} months averaged "
            f"{mean:.1f}% (sd {sd:.2f} pp, floor {T['sd_floor_pp']} pp), giving rolling z = {z:.1f} "
            f"(alert threshold {T['z_alert']})."
        ]
        if yoy is None:
            reasons.append("No year-over-year comparison is available (month 12 months earlier is absent), "
                           f"so this month can be at most 'watch' and only if z >= {T['z_watch_no_yoy']}.")
        else:
            reasons.append(f"Billed units are {m['actual_units']:.0f} kWh versus {ref['actual_units']:.0f} kWh "
                           f"a year earlier ({yoy:+.1f}% year over year; alert threshold {T['yoy_alert_pct']}%).")
        if status == "alert":
            reasons.append("Alert: both the year-over-year rise and the unexplained-share spike exceed their thresholds.")
        elif status == "watch":
            reasons.append("Watch: only one of the two signals exceeds its threshold.")
        else:
            reasons.append("Normal: no threshold combination is met.")
        m["reasons"] = reasons


# --------------------------------------------------------------------------------------
# Step 4: attribution
# --------------------------------------------------------------------------------------
def _prepare_pump_log(pump_log: pd.DataFrame) -> pd.DataFrame:
    pl = pump_log.copy()
    pl["_month"] = pl["date"].astype(str).str[:7]
    return pl


def pump_month_stats(pl: pd.DataFrame, pump_id: str, month: str):
    sub = pl[(pl["_month"] == month) & (pl["pump_id"] == pump_id)]
    if sub.empty:
        return None
    total_min = float(sub["runtime_min"].sum())
    d = {"month": month, "cycles": int(len(sub)), "total_runtime_h": total_min / 60.0,
         "avg_daily_h": total_min / 60.0 / _days(month)}
    if pump_id == "P1":
        bad = sub["pressure_switch_status"] != "OK"
        d["switch_not_ok_cycles"] = int(bad.sum())
        d["switch_not_ok_share"] = float(bad.mean())
        d["status_counts"] = {str(k): int(v) for k, v in sorted(sub["pressure_switch_status"].value_counts().items())}
        tank = pd.to_numeric(sub["tank_level_start_pct"], errors="coerce")
        d["avg_tank_start_pct"] = float(tank.mean()) if tank.notna().any() else None
    return d


def _round_stats(s):
    if s is None:
        return None
    out = {}
    for k, v in s.items():
        if isinstance(v, float):
            out[k] = _r(v, 3)
        else:
            out[k] = v
    return out


def attribute(alert: dict, bills_by_month: dict, inv_by_id: dict, pl: pd.DataFrame) -> dict:
    T = THRESHOLDS
    month = alert["month"]
    last_year = _shift_year(month, -1)
    bill = bills_by_month[month]
    ref_bill = bills_by_month.get(last_year)
    marginal = marginal_inr_per_kwh(bill)
    bill_excess = alert["actual_units"] - ref_bill["total_units_kwh"] if ref_bill else None

    logged_months = set(pl["_month"].unique())
    if last_year in logged_months:
        ref_month = last_year
    elif _prev_month(month) in logged_months:
        ref_month = _prev_month(month)
    else:
        ref_month = None

    stats = {p: {"alert": pump_month_stats(pl, p, month),
                 "ref": pump_month_stats(pl, p, ref_month) if ref_month else None} for p in ("P1", "P3")}
    covered = any(stats[p]["alert"] is not None for p in stats)

    out = {"month": month, "actual_units": _i(alert["actual_units"]),
           "reference_month": ref_month}
    if not covered:
        out.update({
            "attribution_evidence": None,
            "hypotheses": [],
            "insufficient_evidence": INSUFFICIENT_EVIDENCE_MSG,
            "recommended_actions": [{"step": 1, "action": "Add runtime logging or install a pump sub-meter "
                                                          "so that the next unexplained rise can be attributed."}],
            "expected_monthly_saving": None,
            "pump_excess_kwh": None,
            "bill_excess_vs_last_year_kwh": _r(bill_excess, 1),
            "attribution_coverage": None,
            "coverage_label": None,
            "marginal_inr_per_kwh": _r(marginal, 4),
            "excess_cost_inr": None,
        })
        return out

    # Per-pump comparison
    evidence, abnormal_excess = {}, []
    for p in ("P1", "P3"):
        a, r = stats[p]["alert"], stats[p]["ref"]
        ratio = delta = None
        abnormal = False
        excess = None
        if a is not None and r is not None:
            delta = a["avg_daily_h"] - r["avg_daily_h"]
            ratio = a["avg_daily_h"] / r["avg_daily_h"] if r["avg_daily_h"] > 0 else None
            abnormal = bool((ratio is not None and ratio >= T["pump_abnormal_ratio"])
                            or delta >= T["pump_abnormal_delta_h_per_day"])
            if abnormal:
                inv = inv_by_id[p]
                excess = (a["total_runtime_h"] - r["total_runtime_h"]) * float(inv["rated_kw_per_unit"]) * float(inv["quantity"])
                abnormal_excess.append(excess)
        evidence[p] = {"alert_month": _round_stats(a), "reference_month": _round_stats(r),
                       "runtime_ratio": _r(ratio, 3), "delta_h_per_day": _r(delta, 3),
                       "abnormal": abnormal, "excess_kwh": _r(excess, 1)}

    # Hypotheses
    hyps = []
    a1, r1 = stats["P1"]["alert"], stats["P1"]["ref"]
    switch_fired = tank_fired = False
    if a1 is not None and a1["switch_not_ok_share"] >= T["switch_not_ok_share"]:
        switch_fired = True
        counts = ", ".join(f"{k}: {v}" for k, v in a1["status_counts"].items())
        hyps.append({"pump": "P1", "hypothesis": "Pressure switch likely faulty or stuck", "confidence": "high",
                     "evidence": [f"P1: {a1['switch_not_ok_cycles']} of {a1['cycles']} logged cycles in {month} "
                                  f"({a1['switch_not_ok_share'] * 100:.1f}%) had pressure_switch_status other than OK "
                                  f"(threshold {T['switch_not_ok_share'] * 100:.0f}%).",
                                  f"Status counts in {month}: {counts}."]})
    if (a1 is not None and r1 is not None and a1.get("avg_tank_start_pct") is not None
            and r1.get("avg_tank_start_pct") is not None
            and a1["avg_tank_start_pct"] - r1["avg_tank_start_pct"] >= T["tank_start_rise_points"]):
        tank_fired = True
        rise = a1["avg_tank_start_pct"] - r1["avg_tank_start_pct"]
        hyps.append({"pump": "P1",
                     "hypothesis": "Pump restarting at a high tank level: check float/level controller, leakage, overflow",
                     "confidence": "medium",
                     "evidence": [f"P1 average tank level at pump start rose from {r1['avg_tank_start_pct']:.1f}% "
                                  f"in {ref_month} to {a1['avg_tank_start_pct']:.1f}% in {month} "
                                  f"(+{rise:.1f} points; threshold {T['tank_start_rise_points']:.0f})."]})
    for p in ("P1", "P3"):
        ev = evidence[p]
        if ev["runtime_ratio"] is not None and ev["runtime_ratio"] >= T["pump_abnormal_ratio"]:
            if p == "P1" and (switch_fired or tank_fired):
                continue
            hyps.append({"pump": p, "hypothesis": "Higher water demand or leakage", "confidence": "low",
                         "evidence": [f"{p} average daily runtime rose from {ev['reference_month']['avg_daily_h']:.2f} h "
                                      f"in {ref_month} to {ev['alert_month']['avg_daily_h']:.2f} h in {month} "
                                      f"(ratio {ev['runtime_ratio']:.2f}; threshold {T['pump_abnormal_ratio']})."]})
    hyps.sort(key=lambda h: (HYP_RANK[h["confidence"]], h["pump"]))
    # Runtime evidence on the top-ranked pump hypothesis, for context
    for h in hyps:
        ev = evidence[h["pump"]]
        if ev["runtime_ratio"] is not None and h["confidence"] != "low":
            h["evidence"].append(f"{h['pump']} average daily runtime: {ev['reference_month']['avg_daily_h']:.2f} h in "
                                 f"{ref_month} versus {ev['alert_month']['avg_daily_h']:.2f} h in {month} "
                                 f"(ratio {ev['runtime_ratio']:.2f}, +{ev['delta_h_per_day']:.2f} h/day).")

    pump_excess = float(sum(abnormal_excess)) if abnormal_excess else None
    coverage = label = None
    if pump_excess is not None and bill_excess is not None and bill_excess > 0:
        coverage = pump_excess / bill_excess
        if T["coverage_most_low"] <= coverage <= T["coverage_most_high"]:
            label = "explains most of the increase"
        elif coverage > T["coverage_most_high"]:
            label = "may overstate the increase"
        else:
            label = "explains part of the increase"
    excess_cost = pump_excess * marginal if pump_excess is not None else None

    actions = []
    if hyps:
        r1h = stats["P1"]["ref"]["avg_daily_h"] if stats["P1"]["ref"] else None
        tol = T["success_p1_hours_tolerance_pct"] / 100.0
        success = {"p1_avg_daily_hours_within_pct_of_reference": T["success_p1_hours_tolerance_pct"],
                   "p1_reference_avg_daily_hours": _r(r1h, 2),
                   "p1_target_range_h_per_day": [_r(r1h * (1 - tol), 2), _r(r1h * (1 + tol), 2)] if r1h else None,
                   "bill_yoy_band_pct": T["success_yoy_band_pct"]}
        saving = ({"kwh": _i(pump_excess), "inr": _i(excess_cost)} if pump_excess is not None else None)
        actions = [
            {"step": 1, "action": "Inspect and replace the pump pressure switch and controller relay",
             "owner": "electrician", "expected_monthly_saving": saving},
            {"step": 2, "action": "Check tanks and pipes for leakage or overflow", "owner": "plumber"},
            {"step": 3, "action": "Install a sub-meter on the pump (measure instead of estimate)"},
            {"step": 4, "action": "Compare next month: success means P1 average daily hours within "
                                  f"{T['success_p1_hours_tolerance_pct']:.0f}% of the reference and bill year-over-year "
                                  f"within +/-{T['success_yoy_band_pct']:.0f}%",
             "success_criteria": success},
        ]
    out.update({
        "attribution_evidence": {"reference_month": ref_month, "pumps": evidence},
        "hypotheses": hyps,
        "insufficient_evidence": None,
        "recommended_actions": actions,
        "expected_monthly_saving": ({"kwh": _i(pump_excess), "inr": _i(excess_cost)}
                                    if pump_excess is not None else None),
        "pump_excess_kwh": _r(pump_excess, 1),
        "bill_excess_vs_last_year_kwh": _r(bill_excess, 1),
        "attribution_coverage": _r(coverage, 3),
        "coverage_label": label,
        "marginal_inr_per_kwh": _r(marginal, 4),
        "excess_cost_inr": _r(excess_cost, 1),
    })
    return out


# --------------------------------------------------------------------------------------
# Main entry points
# --------------------------------------------------------------------------------------
def _analyze(bills: pd.DataFrame, inventory: pd.DataFrame, pump_log: pd.DataFrame,
             dg_log: pd.DataFrame, tariff: dict) -> dict:
    T = THRESHOLDS
    bill_rows = sorted(bills.to_dict("records"), key=lambda r: r["month"])
    bill_rows = [{k: (float(v) if k not in ("month", "billing_period_start", "billing_period_end") else v)
                  for k, v in r.items()} for r in bill_rows]
    bills_by_month = {r["month"]: r for r in bill_rows}
    inv_rows = inventory.to_dict("records")
    inv_by_id = {r["equipment_id"]: r for r in inv_rows}
    pl = _prepare_pump_log(pump_log)

    # Steps 1 and 2
    months = []
    for b in bill_rows:
        est = estimate_month(inv_rows, b["month"])
        est_total = float(sum(est.values()))
        actual = b["total_units_kwh"]
        unexp = actual - est_total
        pct = unexp / actual * 100.0
        months.append({"month": b["month"], "actual_units": actual, "_est": est, "_est_total": est_total,
                       "unexplained_kwh": unexp, "unexplained_pct": pct, "confidence": confidence_label(pct)})
    flag_months(months)
    month_by_id = {m["month"]: m for m in months}

    # Step 4/5: alerts
    alerts = [attribute(m, bills_by_month, inv_by_id, pl) for m in months if m["status"] == "alert"]

    # Lighting opportunity (latest month)
    latest = months[-1]["month"]
    latest_marginal = marginal_inr_per_kwh(bills_by_month[latest])
    opportunities = []
    for row in inv_rows:
        if row["equipment_type"] == "lighting" and str(row["control_type"]) == "manual":
            kwh = estimate_row_kwh(row, latest)
            frac = ASSUMPTIONS["lighting_manual_saving_fraction"]
            opportunities.append({
                "type": "lighting_control", "equipment_id": row["equipment_id"], "name": row["name"],
                "location": row["location"], "month": latest, "monthly_kwh": _r(kwh, 1),
                "assumed_saving_fraction": frac, "illustrative_saving_kwh": _r(kwh * frac, 1),
                "illustrative_saving_inr": _r(kwh * frac * latest_marginal, 1),
                "label": ASSUMPTIONS["lighting_manual_saving_label"],
                "suggestion": "Fixtures are switched manually; consider timer or sensor control."})

    # Step 6: tariff what-if
    diff = float(tariff["stp_commercial_rate"]) - float(tariff["stp_residential_common_rate"])
    stp_latest = months[-1]["_est"]["stp"]
    stp_12 = float(sum(m["_est"]["stp"] for m in months[-12:]))
    tariff_whatif = {
        "statement": "Rates are placeholders, not actual BESCOM tariff-order values.",
        "tariff_file_note": tariff.get("note"),
        "stp_residential_common_rate": float(tariff["stp_residential_common_rate"]),
        "stp_commercial_rate": float(tariff["stp_commercial_rate"]),
        "rate_difference_inr_per_kwh": _r(diff, 2),
        "latest_month": latest,
        "stp_estimated_kwh_latest_month": _r(stp_latest, 1),
        "extra_cost_latest_month_inr": _r(stp_latest * diff, 1),
        "last_12_months": [months[-12]["month"], latest],
        "stp_estimated_kwh_last_12_months": _r(stp_12, 1),
        "extra_cost_last_12_months_inr": _r(stp_12 * diff, 1),
    }

    # Post-fix (latest alert that has a following month)
    post_fix = None
    for a in reversed(alerts):
        idx = [m["month"] for m in months].index(a["month"])
        if idx + 1 >= len(months):
            continue
        nxt = months[idx + 1]["month"]
        s_alert = pump_month_stats(pl, "P1", a["month"])
        s_next = pump_month_stats(pl, "P1", nxt)
        if s_alert is None or s_next is None:
            post_fix = {"alert_month": a["month"], "following_month": nxt, "available": False,
                        "reason": "pump log does not cover both months; no savings claimed"}
            break
        drop = s_alert["avg_daily_h"] - s_next["avg_daily_h"]
        kw = float(inv_by_id["P1"]["rated_kw_per_unit"]) * float(inv_by_id["P1"]["quantity"])
        saving_kwh = max(0.0, drop) * _days(nxt) * kw
        rate = marginal_inr_per_kwh(bills_by_month[nxt])
        post_fix = {"alert_month": a["month"], "following_month": nxt, "available": True,
                    "p1_avg_daily_hours_alert_month": _r(s_alert["avg_daily_h"], 3),
                    "p1_avg_daily_hours_following_month": _r(s_next["avg_daily_h"], 3),
                    "hours_drop_per_day": _r(drop, 3),
                    "monthly_saving_kwh": _r(saving_kwh, 1),
                    "monthly_saving_inr": _r(saving_kwh * rate, 1),
                    "marginal_inr_per_kwh": _r(rate, 4),
                    "following_month_yoy_pct": _r(month_by_id[nxt]["yoy_pct"], 2),
                    "note": "Saving is derived only from the P1 pump log (nameplate kW, days of the following month)."}
        break

    # DG summary (kept separate from BESCOM units)
    dg = dg_log.copy()
    dg["_month"] = dg["date"].astype(str).str[:7]
    per_month = []
    for m in months:
        sub = dg[dg["_month"] == m["month"]]
        per_month.append({"month": m["month"], "run_hours": _r(sub["run_hours"].sum(), 2),
                          "cost_inr": _r(sub["cost_inr"].sum(), 2), "events": int(len(sub))})
    last12 = per_month[-12:]
    dg_summary = {"note": "Diesel generator cost is separate from BESCOM units and is not subtracted from them.",
                  "monthly": per_month,
                  "last_12_months": [last12[0]["month"], last12[-1]["month"]],
                  "last_12_months_total_cost_inr": _r(sum(x["cost_inr"] for x in last12), 2),
                  "last_12_months_total_run_hours": _r(sum(x["run_hours"] for x in last12), 2)}

    # Months output
    months_out = []
    for m in months:
        months_out.append({
            "month": m["month"], "actual_units": _i(m["actual_units"]),
            "estimated_by_category": {c: _r(m["_est"][c], 2) for c in CATEGORIES},
            "estimated_total": _r(m["_est_total"], 2), "unexplained_kwh": _r(m["unexplained_kwh"], 2),
            "unexplained_pct": _r(m["unexplained_pct"], 2), "confidence": m["confidence"],
            "yoy_pct": _r(m["yoy_pct"], 2), "rolling_z": _r(m["rolling_z"], 2),
            "status": m["status"], "reasons": m["reasons"]})

    # AGM facts: flat, numbers only, with a parallel label dict
    facts = []

    def add(key, label, value):
        if value is not None:
            facts.append((key, label, value))

    lm = months[-1]
    add("latest_month_actual_units_kwh", f"Billed units, latest month ({lm['month']}), kWh", _i(lm["actual_units"]))
    add("latest_month_estimated_total_kwh", "Estimated consumption by equipment, latest month, kWh", _i(lm["_est_total"]))
    add("latest_month_unexplained_kwh", "Unexplained consumption, latest month, kWh", _i(lm["unexplained_kwh"]))
    add("latest_month_unexplained_pct", "Unexplained share of billed units, latest month, %", _r(lm["unexplained_pct"], 1))
    if alerts:
        a = alerts[-1]
        am = month_by_id[a["month"]]
        ref_units = bills_by_month[_shift_year(a["month"], -1)]["total_units_kwh"]
        add("alert_actual_units_kwh", f"Billed units in alert month ({a['month']}), kWh", _i(am["actual_units"]))
        add("alert_last_year_units_kwh", "Billed units in the same month a year earlier, kWh", _i(ref_units))
        add("alert_yoy_pct", "Year-over-year change in billed units, alert month, %", _r(am["yoy_pct"], 1))
        add("alert_rolling_z", "Rolling z-score of unexplained share, alert month", _r(am["rolling_z"], 1))
        add("alert_unexplained_pct", "Unexplained share of billed units, alert month, %", _r(am["unexplained_pct"], 1))
        add("bill_excess_vs_last_year_kwh", "Bill increase versus same month last year, kWh", _i(a["bill_excess_vs_last_year_kwh"]))
        ev = (a["attribution_evidence"] or {}).get("pumps", {}).get("P1") if a["attribution_evidence"] else None
        if ev:
            if ev["alert_month"]:
                add("p1_alert_avg_daily_hours", "P1 average daily runtime, alert month, h/day", _r(ev["alert_month"]["avg_daily_h"], 1))
                add("p1_switch_not_ok_pct", "P1 cycles with pressure switch status not OK, alert month, %",
                    _r(ev["alert_month"]["switch_not_ok_share"] * 100, 1))
                add("p1_alert_tank_start_pct", "P1 average tank level at pump start, alert month, %",
                    _r(ev["alert_month"].get("avg_tank_start_pct"), 1))
            if ev["reference_month"]:
                add("p1_reference_avg_daily_hours", "P1 average daily runtime, reference month, h/day", _r(ev["reference_month"]["avg_daily_h"], 1))
                add("p1_reference_tank_start_pct", "P1 average tank level at pump start, reference month, %",
                    _r(ev["reference_month"].get("avg_tank_start_pct"), 1))
            add("p1_runtime_ratio", "P1 runtime ratio, alert month versus reference (2 decimals)", ev["runtime_ratio"] and _r(ev["runtime_ratio"], 2))
            add("p1_delta_hours_per_day", "P1 extra runtime versus reference, h/day", _r(ev["delta_h_per_day"], 1))
        add("pump_excess_kwh", "Estimated excess pump consumption, nameplate kW, kWh", _i(a["pump_excess_kwh"]))
        add("attribution_coverage_pct", "Share of the bill increase explained by pump excess, %",
            _r(a["attribution_coverage"] * 100, 1) if a["attribution_coverage"] is not None else None)
        add("excess_cost_inr", "Cost of the excess pump consumption, INR", _i(a["excess_cost_inr"]))
        add("marginal_inr_per_kwh", "Marginal cost per kWh incl. tax, INR (2 decimals)", _r(a["marginal_inr_per_kwh"], 2))
    if post_fix and post_fix.get("available"):
        add("p1_following_avg_daily_hours", f"P1 average daily runtime, month after alert ({post_fix['following_month']}), h/day",
            _r(post_fix["p1_avg_daily_hours_following_month"], 1))
        add("post_fix_saving_kwh", "Monthly saving after the fix, from the pump log, kWh", _i(post_fix["monthly_saving_kwh"]))
        add("post_fix_saving_inr", "Monthly saving after the fix, from the pump log, INR", _i(post_fix["monthly_saving_inr"]))
        add("following_month_yoy_pct", "Year-over-year change in billed units, month after alert, %", _r(post_fix["following_month_yoy_pct"], 1))
    add("stp_estimated_kwh_latest_month", "STP estimated consumption, latest month, kWh", _i(stp_latest))
    add("stp_estimated_kwh_last_12_months", "STP estimated consumption, last 12 months, kWh", _i(stp_12))
    add("tariff_whatif_extra_latest_month_inr", "Placeholder tariff what-if: extra STP cost, latest month, INR", _i(stp_latest * diff))
    add("tariff_whatif_extra_last_12_months_inr", "Placeholder tariff what-if: extra STP cost, last 12 months, INR", _i(stp_12 * diff))
    add("dg_cost_latest_month_inr", "Diesel generator cost, latest month, INR (separate from BESCOM)", _i(per_month[-1]["cost_inr"]))
    add("dg_cost_last_12_months_inr", "Diesel generator cost, last 12 months, INR (separate from BESCOM)", _i(dg_summary["last_12_months_total_cost_inr"]))
    for o in opportunities:
        add(f"opportunity_{o['equipment_id'].lower()}_monthly_kwh", f"{o['name']}: monthly consumption, kWh", _i(o["monthly_kwh"]))
        add(f"opportunity_{o['equipment_id'].lower()}_illustrative_saving_kwh",
            f"{o['name']}: illustrative saving at {int(o['assumed_saving_fraction'] * 100)}%, kWh ({o['label']})",
            _i(o["illustrative_saving_kwh"]))

    result = {
        "meta": {
            "thresholds": dict(THRESHOLDS),
            "assumptions": json.loads(json.dumps(ASSUMPTIONS)),
            "data_window": {"first_month": months[0]["month"], "last_month": months[-1]["month"],
                            "months": len(months),
                            "pump_log_months": sorted(pl["_month"].unique().tolist())},
            "note": SYNTHETIC_NOTE,
        },
        "months": months_out,
        "alerts": alerts,
        "opportunities": opportunities,
        "tariff_whatif": tariff_whatif,
        "post_fix": post_fix,
        "dg_summary": dg_summary,
        "agm_facts": {k: v for k, _, v in facts},
        "agm_facts_labels": {k: lab for k, lab, _ in facts},
    }
    return result

def analyze(data=None, *args, **kwargs) -> dict:
    """Support analyze(data) and the existing positional/keyword API."""
    if isinstance(data, dict):
        if args or kwargs:
            raise TypeError("Pass either a data dictionary or individual inputs")

        inputs = dict(data)

        # Accept the AWS task's 'equipment' name and the existing 'inventory' name.
        if "equipment" in inputs:
            if "inventory" in inputs:
                raise ValueError("Use equipment or inventory, not both")
            inputs["inventory"] = inputs.pop("equipment")

        return _analyze(**inputs)

    if data is not None:
        return _analyze(data, *args, **kwargs)

    return _analyze(*args, **kwargs)

def run(data_dir) -> dict:
    return analyze(**load_data(data_dir))


def to_json(result: dict) -> str:
    return json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n"