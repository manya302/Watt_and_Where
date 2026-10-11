"""Acceptance tests for the Watt & Where analysis engine. Run: pytest -v -s"""
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import engine  # noqa: E402

DATA = ROOT / "data"


@pytest.fixture(scope="module")
def result():
    assert DATA.exists(), "./data is missing; run generate_data.py first"
    return engine.run(DATA)


def _by_month(result):
    return {m["month"]: m for m in result["months"]}


def test_1_statuses(result):
    ms = _by_month(result)
    alerts = [m for m, v in ms.items() if v["status"] == "alert"]
    watches = [m for m, v in ms.items() if v["status"] == "watch"]
    print(f"\n[1] alerts={alerts} watches={watches} 2024-12={ms['2024-12']['status']} "
          f"(z={ms['2024-12']['rolling_z']}) 2025-05={ms['2025-05']['status']} (z={ms['2025-05']['rolling_z']}, "
          f"yoy={ms['2025-05']['yoy_pct']})")
    assert ms["2026-03"]["status"] == "alert"
    assert alerts == ["2026-03"]
    assert len(watches) <= 2
    assert ms["2024-12"]["status"] == "normal"
    assert ms["2025-05"]["status"] == "normal"
    first_year = [m for m, v in ms.items() if v["yoy_pct"] is None]
    assert all(ms[m]["status"] != "alert" for m in first_year)


def test_2_attribution(result):
    a = [x for x in result["alerts"] if x["month"] == "2026-03"][0]
    p1 = a["attribution_evidence"]["pumps"]["P1"]
    print(f"\n[2] top hypothesis={a['hypotheses'][0]['hypothesis']!r} ({a['hypotheses'][0]['confidence']}), "
          f"P1 ratio={p1['runtime_ratio']}, pump_excess_kwh={a['pump_excess_kwh']}, "
          f"bill_excess={a['bill_excess_vs_last_year_kwh']}, coverage={a['attribution_coverage']} "
          f"({a['coverage_label']}), excess_cost_inr={a['excess_cost_inr']}, reference={a['reference_month']}")
    assert "pressure switch" in a["hypotheses"][0]["hypothesis"].lower()
    assert 1.8 <= p1["runtime_ratio"] <= 2.0
    assert 600 <= a["pump_excess_kwh"] <= 720
    assert 0.8 <= a["attribution_coverage"] <= 1.4


def test_3_no_peeking(result, tmp_path):
    clean = tmp_path / "data"
    shutil.copytree(DATA, clean)
    (clean / "monthly_truth.csv").unlink()
    assert not (clean / "monthly_truth.csv").exists()
    a = engine.to_json(engine.run(DATA))
    b = engine.to_json(engine.run(clean))
    print(f"\n[3] identical output without monthly_truth.csv: {a == b} ({len(a)} chars)")
    assert a == b


def test_4_no_pump_log(tmp_path):
    d = tmp_path / "data"
    shutil.copytree(DATA, d)
    (d / "pump_log.csv").unlink()
    res = engine.run(d)
    ms = _by_month(res)
    alert = [x for x in res["alerts"] if x["month"] == "2026-03"]
    print(f"\n[4] 2026-03 status={ms['2026-03']['status']}, alerts={[x['month'] for x in res['alerts']]}, "
          f"hypotheses={alert[0]['hypotheses']}, message={alert[0]['insufficient_evidence']!r}, "
          f"pump_excess_kwh={alert[0]['pump_excess_kwh']}")
    assert ms["2026-03"]["status"] == "alert"
    assert len(alert) == 1
    assert alert[0]["hypotheses"] == []
    assert "insufficient evidence" in alert[0]["insufficient_evidence"]
    assert alert[0]["pump_excess_kwh"] is None


def test_5_determinism(tmp_path):
    outs = []
    for i in (1, 2):
        out = tmp_path / f"run{i}" / "analysis_result.json"
        proc = subprocess.run([sys.executable, str(ROOT / "run_analysis.py"), "--data-dir", str(DATA),
                               "--output", str(out)], capture_output=True, text=True, cwd=ROOT)
        assert proc.returncode == 0, proc.stderr
        outs.append(out.read_bytes())
    print(f"\n[5] byte-identical: {outs[0] == outs[1]} ({len(outs[0])} bytes)")
    assert outs[0] == outs[1]


def test_6_json_validity(result):
    text = engine.to_json(result)

    def reject(c):
        raise ValueError(f"non-finite constant in JSON: {c}")

    parsed = json.loads(text, parse_constant=reject)
    facts = parsed["agm_facts"]
    bad = [k for k, v in facts.items() if isinstance(v, bool) or not isinstance(v, (int, float))
           or (isinstance(v, float) and not math.isfinite(v))]
    print(f"\n[6] parses OK, 'NaN' in text: {'NaN' in text}, agm_facts keys={len(facts)}, "
          f"non-numeric={bad}, labels for every key: {set(facts) == set(parsed['agm_facts_labels'])}")
    assert "NaN" not in text
    assert not bad
    assert set(parsed["agm_facts_labels"]) == set(facts)


def test_7_report_only_vs_truth(result):
    truth = pd.read_csv(DATA / "monthly_truth.csv").set_index("month")
    cols = {"pump": "pumps_kwh", "lift": "lifts_kwh", "stp": "stp_kwh",
            "water_treatment": "water_treatment_kwh", "lighting": "lighting_kwh"}
    ms = _by_month(result)
    print("\n[7] REPORT ONLY: mean absolute % error of estimate vs truth (all 25 months)")
    for cat, col in cols.items():
        est = np.array([ms[m]["estimated_by_category"][cat] for m in truth.index])
        mape = float(np.mean(np.abs(est - truth[col].values) / truth[col].values) * 100)
        print(f"    {cat:16s} MAPE = {mape:5.2f}%")
    avg_unexp = float(np.mean([m["unexplained_pct"] for m in result["months"]]))
    avg_unexp_ex = float(np.mean([m["unexplained_pct"] for m in result["months"] if m["month"] != "2026-03"]))
    print(f"    average unexplained_pct = {avg_unexp:.2f}% (excluding 2026-03: {avg_unexp_ex:.2f}%)")
    print(f"    (the truth's unmetered 'other' load is ~{truth['other_kwh'].mean():.0f} kWh/month, "
          f"which the engine does not estimate)")


def test_8_seed_robustness():
    gen = ROOT / "generate_data.py"
    if not gen.exists():
        pytest.skip("generate_data.py not available; skipping seed robustness check")
    src = gen.read_text()
    assert "default_rng(42)" in src
    import tempfile
    clean, details = 0, []
    for seed in range(1, 21):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            (td / "gen.py").write_text(src.replace("default_rng(42)", f"default_rng({seed})"))
            proc = subprocess.run([sys.executable, "gen.py"], cwd=td, capture_output=True, text=True)
            if proc.returncode != 0:
                details.append((seed, "generator error: " + proc.stderr.strip().splitlines()[-1]))
                continue
            res = engine.run(td / "data")
            alerts = [m["month"] for m in res["months"] if m["status"] == "alert"]
            watches = [m["month"] for m in res["months"] if m["status"] == "watch"]
            ok = alerts == ["2026-03"]
            clean += ok
            if not ok or watches:
                details.append((seed, f"alerts={alerts} watches={watches}"))
    print(f"\n[8] seeds 1-20: only 2026-03 alerts in {clean}/20 runs (target >= 18)")
    for d in details:
        print(f"    seed {d[0]}: {d[1]}")
    assert clean >= 18