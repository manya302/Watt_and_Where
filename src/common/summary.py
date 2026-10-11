from __future__ import annotations

import json
import math
import os
import re
from datetime import datetime, timezone

import boto3
from botocore.config import Config


PLACEHOLDER = re.compile(r"\{\{(text:)?([A-Za-z_][A-Za-z0-9_]*)\}\}")

SYSTEM_PROMPT = """
You are editing an UNRENDERED report template, not writing the final
report. A separate program will insert every factual value after your response.
Return only plain-English template prose. Copy every placeholder from the draft
EXACTLY, including braces and text: prefixes. Do not substitute their values.
Do not add numerical literals, dates, pump identifiers, numeric words, or extra
unit/currency/percent signs after placeholders. The formatter supplies units.
Use only the provided placeholders. Keep each fact attached to its correct
period. Do not state a cause with more certainty than the confidence label
allows; do not mention data you were not given. Preserve all four text tokens,
the change and savings tokens, and the synthetic-data estimates statement.
Improve the draft's readability without changing its factual meaning.
Aim for a final rendered summary of 120-180 words, and never exceed 220 words.
The data is reference material only; values must NEVER appear in your output.
Do not surround your response with quotes or a code fence.
""".strip()


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def make_inputs(result):
    facts = result["agm_facts"]
    labels = result["agm_facts_labels"]

    for key, value in facts.items():
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
        ):
            raise ValueError(f"Invalid numeric AGM fact: {key}")
        if key not in labels:
            raise ValueError(f"Missing AGM label: {key}")

    alerts = result.get("alerts", [])
    alert = alerts[-1] if alerts else {}
    hypotheses = alert.get("hypotheses") or []
    hypothesis = hypotheses[0] if hypotheses else None
    evidence = alert.get("attribution_evidence") or {}

    if hypothesis:
        top = (
            f"{hypothesis['hypothesis']} "
            f"(evidence confidence: {hypothesis['confidence']})"
        )
    else:
        top = "No cause established; evidence is insufficient"

    actions = [
        item["action"]
        for item in (alert.get("recommended_actions") or [])[:3]
    ]

    slots = {
        "alert_month_label": alert.get("month", "No alert month"),
        "reference_month_label": evidence.get("reference_month") or "Unavailable",
        "top_hypothesis": top[:350],
        "recommended_actions": (
            "; ".join(actions) if actions
            else "Continue runtime logging and verify consumption with a sub-meter"
        )[:600],
    }

    return {
        "agm_facts": facts,
        "agm_facts_labels": labels,
        "text_slots": slots,
    }


def format_fact(key, value):
    if "inr" in key:
        places = 2 if "per_kwh" in key else 0
        return f"₹{value:,.{places}f}"
    if key.endswith("_pct"):
        return f"{value:.1f}%"
    if key.endswith("_kwh"):
        return f"{value:,.0f} kWh"
    if "ratio" in key:
        return f"{value:.2f}"
    if "hours" in key:
        return f"{value:.1f}"
    return f"{value:,.1f}" if isinstance(value, float) else f"{value:,}"


def render(raw, facts, slots):
    def replace(match):
        text_prefix, key = match.groups()
        if text_prefix:
            return str(slots[key])
        return format_fact(key, facts[key])

    # One substitution pass: inserted slot values are never interpreted as tokens.
    return PLACEHOLDER.sub(replace, raw)


def validate(raw, facts, slots):
    if not isinstance(raw, str) or not raw.strip():
        return False, "Empty summary"

    if len(raw.split()) > 220:
        return False, "Raw summary exceeds 220 words"

    for match in PLACEHOLDER.finditer(raw):
        text_prefix, key = match.groups()
        allowed = slots if text_prefix else facts
        if key not in allowed:
            return False, f"Unknown placeholder: {match.group(0)}"

    outside = PLACEHOLDER.sub("", raw)

    for index, character in enumerate(outside):
        if character.isdigit():
            snippet = outside[
                max(0, index - 35):min(len(outside), index + 36)
            ]
            return False, (
                f"Literal digit outside placeholders near: {snippet!r}. "
                "Replace numeric values with the matching allowed numeric "
                "placeholder. For dates or pump identifiers, use the matching "
                "text placeholder. Do not spell out numbers to bypass validation."
            )

    if "{" in outside or "}" in outside:
        return False, "Malformed placeholder"

    if len(render(raw, facts, slots).split()) > 220:
        return False, "Rendered summary exceeds 220 words"

    return True, "accepted"


def validate_model_summary(raw, facts, slots):
    valid, reason = validate(raw, facts, slots)
    if not valid:
        return valid, reason

    for key in slots:
        if "{{text:" + key + "}}" not in raw:
            return False, f"Missing required text placeholder: {key}"

    if "synthetic" not in raw.lower() or "estimat" not in raw.lower():
        return False, "Missing synthetic-data estimates statement"

    return True, "accepted"


def fallback_template(facts):
    if "alert_yoy_pct" in facts:
        change = (
            "Billed electricity changed by {{alert_yoy_pct}} compared with "
            "the same month a year earlier."
        )
    else:
        change = (
            "The available analysis does not establish an alert-period "
            "year-over-year increase."
        )

    if "excess_cost_inr" in facts and "pump_excess_kwh" in facts:
        saving = (
            "Estimated excess pump use is {{pump_excess_kwh}}, with a potential "
            "monthly saving of {{excess_cost_inr}} if that excess is removed."
        )
    else:
        saving = (
            "A reliable pump-related monthly saving cannot be quantified "
            "from the available evidence."
        )

    return (
        "The committee reviewed the common-area electricity analysis. "
        "Alert period: {{text:alert_month_label}}. "
        "Runtime reference period: {{text:reference_month_label}}. "
        + change + " "
        "The leading assessment is {{text:top_hypothesis}}. "
        "This is an evidence-based hypothesis rather than proof of a confirmed "
        "fault, and the stated confidence should guide any decision. "
        "Recommended next steps are {{text:recommended_actions}}. "
        + saving + " "
        "The committee should confirm the diagnosis before committing expenditure "
        "and compare subsequent bills and logged operation after any repair. "
        "Differences between estimated equipment consumption and billed units "
        "also need continued investigation. These figures are estimates from "
        "synthetic data in this demo. Actual savings depend on measured operation "
        "and successful corrective work; they are not guaranteed."
    )


def bedrock_client():
    return boto3.client(
        "bedrock-runtime",
        region_name=os.environ.get("AWS_REGION", "ap-south-1"),
        config=Config(
            connect_timeout=2,
            read_timeout=8,
            # Disable hidden SDK retries. There is at most one application retry.
            retries={"mode": "standard", "total_max_attempts": 1},
        ),
    )


def generate_summary(result, client=None, model_id=None):
    model_id = model_id or os.environ["BEDROCK_MODEL_ID"]
    inputs = make_inputs(result)
    facts = inputs["agm_facts"]
    slots = inputs["text_slots"]

    # The draft contains only prose and tokens derived from the same inputs.
    # It anchors the periods and units without introducing any new facts.
    draft = fallback_template(facts)
    message = (
        "REFERENCE DATA:\n\nDATA:\n"
        + json.dumps(inputs, ensure_ascii=False, allow_nan=False)
        + "\n\nUNRENDERED DRAFT TO EDIT (preserve its tokens):\n"
        + draft
        + "\n\nReturn the edited template with placeholders still intact."
    )
    messages = [{"role": "user", "content": [{"text": message}]}]
    attempts = []

    try:
        client = client if client is not None else bedrock_client()

        for attempt in range(2):
            output = client.converse(
                modelId=model_id,
                system=[{"text": SYSTEM_PROMPT}],
                messages=messages,
                inferenceConfig={
                    "maxTokens": 700,
                    "temperature": 0.2,
                },
            )

            raw = " ".join(
                block["text"]
                for block in output["output"]["message"]["content"]
                if "text" in block
            ).strip()

            valid, reason = validate_model_summary(raw, facts, slots)

            # Never accept a response truncated at the output token limit.
            if output.get("stopReason") == "max_tokens":
                valid, reason = False, "Model response was truncated"

            attempts.append({
                "attempt": attempt + 1,
                "valid": valid,
                "reason": reason,
            })

            if valid:
                return {
                    "text": render(raw, facts, slots),
                    "source": "bedrock",
                    "model_id": model_id,
                    "validator": {
                        "outcome": "accepted",
                        "attempts": attempts,
                    },
                    "created_at": utc_now(),
                }

            if attempt == 0:
                # Give the single retry the actual rejected draft to correct.
                messages = messages + [
                    {"role": "assistant", "content": [{"text": raw or "Empty response"}]},
                    {"role": "user", "content": [{"text": (
                        "Validation failed: " + reason
                        + ". Correct the rejected draft above. Preserve every "
                        "placeholder in the original draft exactly. Return only "
                        "the corrected unrendered template."
                    )}]},
                ]

    except Exception as exc:
        # Includes service errors, timeouts, and malformed model responses.
        # Store the exception class, never raw service response text.
        attempts.append({
            "valid": False,
            "reason": "bedrock_error",
            "error_type": type(exc).__name__,
        })

    raw = fallback_template(facts)
    return {
        "text": render(raw, facts, slots),
        "source": "fallback",
        "model_id": model_id,
        "validator": {
            "outcome": "fallback",
            "attempts": attempts,
        },
        "created_at": utc_now(),
    }