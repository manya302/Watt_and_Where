from __future__ import annotations

import html
import json


def escape(value):
    return html.escape(str(value), quote=True)


def json_section(title, value):
    return (
        f"<section><h2>{escape(title)}</h2>"
        f"<pre>{escape(json.dumps(value, indent=2, ensure_ascii=False))}</pre>"
        "</section>"
    )


def build_report(result, summary):
    bill_rows = "".join(
        "<tr>"
        f"<td>{escape(month['month'])}</td>"
        f"<td>{escape(month['actual_units'])}</td>"
        f"<td>{escape(month['estimated_total'])}</td>"
        f"<td>{escape(month['unexplained_pct'])}</td>"
        f"<td>{escape(month['status'])}</td>"
        "</tr>"
        for month in result["months"]
    )

    latest = result["months"][-1]
    split_rows = "".join(
        f"<tr><td>{escape(category)}</td><td>{escape(kwh)}</td></tr>"
        for category, kwh in latest["estimated_by_category"].items()
    )

    alert_details = []
    for alert in result.get("alerts", []):
        alert_details.append({
            "month": alert["month"],
            "hypotheses": alert.get("hypotheses"),
            "evidence": alert.get("attribution_evidence"),
            "recommended_actions": alert.get("recommended_actions"),
            "expected_monthly_saving": alert.get("expected_monthly_saving"),
            "insufficient_evidence": alert.get("insufficient_evidence"),
        })

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy"
      content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'">
<title>Watt &amp; Where — AGM report</title>
<style>
body {{ max-width: 1000px; margin: 40px auto; padding: 0 20px;
        color: #172b3a; font: 16px/1.6 system-ui, sans-serif; }}
h1, h2 {{ line-height: 1.2; }}
table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
th, td {{ border: 1px solid #cbd5df; padding: 9px; text-align: left; }}
th {{ background: #edf3f7; }}
pre {{ white-space: pre-wrap; overflow-wrap: anywhere; background: #f5f7fa;
       padding: 16px; font-size: 13px; }}
.summary {{ white-space: pre-wrap; }}
</style>
</head>
<body>
<h1>Watt &amp; Where</h1>
<p>Sunrise Heights · Synthetic-data demonstration</p>

<h2>AGM summary</h2>
<p class="summary">{escape(summary["text"])}</p>
<p>Summary source: {escape(summary["source"])}</p>

<h2>Monthly bill chart data</h2>
<table>
<thead><tr><th>Month</th><th>Billed kWh</th><th>Estimated kWh</th>
<th>Unexplained %</th><th>Status</th></tr></thead>
<tbody>{bill_rows}</tbody>
</table>

<h2>Estimated equipment split — {escape(latest["month"])}</h2>
<table><thead><tr><th>Category</th><th>kWh</th></tr></thead>
<tbody>{split_rows}</tbody></table>

{json_section("Alerts, evidence and recommendations", alert_details)}
{json_section("Other opportunities", result.get("opportunities", []))}
{json_section("Tariff assumptions", result.get("tariff_whatif", {}))}
{json_section("Post-fix comparison", result.get("post_fix"))}
{json_section("Diesel generator — separate from electricity units",
              result.get("dg_summary", {}))}

<p>Figures are estimates from synthetic data. Potential savings require
verification through measured operation.</p>
</body></html>
"""