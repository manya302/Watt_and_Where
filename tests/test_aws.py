from __future__ import annotations

import importlib
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import boto3
import pytest
import yaml
from moto import mock_aws


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

import engine
from common import storage
from common.summary import (
    generate_summary,
    make_inputs,
    render,
    validate,
)
from handlers import api
from scripts.load_data import load_dataset


@pytest.fixture(scope="session")
def dataset(tmp_path_factory):
    directory = tmp_path_factory.mktemp("generated")
    subprocess.run(
        [sys.executable, str(ROOT / "generate_data.py")],
        cwd=directory,
        check=True,
        capture_output=True,
        text=True,
    )
    return directory / "data"


@pytest.fixture
def aws(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "ap-south-1")
    monkeypatch.setenv("AWS_REGION", "ap-south-1")
    monkeypatch.setenv("AWS_EC2_METADATA_DISABLED", "true")
    monkeypatch.setenv("TABLE_NAME", "WattWhere")
    monkeypatch.setenv("APARTMENT_ID", "sunrise-heights")
    monkeypatch.setenv("FRONTEND_ORIGIN", "http://localhost:3000")
    monkeypatch.setenv("BEDROCK_MODEL_ID", "test-model")
    monkeypatch.setenv("REPORT_BUCKET", "wattwhere-test-reports")

    with mock_aws():
        db = boto3.resource("dynamodb", region_name="ap-south-1").create_table(
            TableName="WattWhere",
            BillingMode="PAY_PER_REQUEST",
            AttributeDefinitions=[
                {"AttributeName": "apartment_id", "AttributeType": "S"},
                {"AttributeName": "SK", "AttributeType": "S"},
            ],
            KeySchema=[
                {"AttributeName": "apartment_id", "KeyType": "HASH"},
                {"AttributeName": "SK", "KeyType": "RANGE"},
            ],
        )
        s3 = boto3.client("s3", region_name="ap-south-1")
        s3.create_bucket(
            Bucket="wattwhere-test-reports",
            CreateBucketConfiguration={"LocationConstraint": "ap-south-1"},
        )
        yield db


def call(handler, body=None):
    event = {
        "body": body,
        "requestContext": {"requestId": "test-request"},
    }
    result = handler(event, SimpleNamespace(aws_request_id="test-request"))
    return result["statusCode"], json.loads(result["body"])


def scan_all(db):
    items = []
    request = {}
    while True:
        result = db.scan(**request)
        items.extend(result["Items"])
        if "LastEvaluatedKey" not in result:
            return items
        request["ExclusiveStartKey"] = result["LastEvaluatedKey"]


def invalid_client():
    client = Mock()
    client.converse.return_value = {
        "output": {"message": {"content": [{"text": "The saving is 123 rupees."}]}},
        "stopReason": "end_turn",
    }
    return client


def test_loader_idempotent_and_never_reads_truth(dataset, aws, monkeypatch):
    pandas = importlib.import_module("pandas")
    original_read = pandas.read_csv
    seen = []

    def checked_read(path, *args, **kwargs):
        name = Path(path).name
        assert name != "monthly_truth.csv"
        seen.append(name)
        return original_read(path, *args, **kwargs)

    monkeypatch.setattr(pandas, "read_csv", checked_read)

    first = load_dataset(dataset, aws)
    first_items = scan_all(aws)
    second = load_dataset(dataset, aws)
    second_items = scan_all(aws)

    assert first == second == len(first_items) == len(second_items)
    assert {
        (item["apartment_id"], item["SK"]) for item in first_items
    } == {
        (item["apartment_id"], item["SK"]) for item in second_items
    }
    assert set(seen) == {
        "bills.csv", "equipment_inventory.csv", "pump_log.csv", "dg_log.csv"
    }
    assert all(
        item["SK"].startswith(("BILL#", "EQUIP#", "PUMPLOG#", "DG#", "TARIFF#"))
        for item in second_items
    )


def test_analysis_matches_local_engine(dataset, aws):
    load_dataset(dataset, aws)
    local = engine.run(dataset)

    status, cloud = call(api.analysis_run, "{}")
    assert status == 200
    assert [a["month"] for a in cloud["alerts"]] == [
        a["month"] for a in local["alerts"]
    ]
    assert cloud["agm_facts"] == local["agm_facts"]

    status, saved = call(api.analysis_get)
    assert status == 200
    assert saved == cloud

    status, bills = call(api.bills)
    assert status == 200
    assert len(bills["bills"]) == 25
    assert all("total_amount" in bill for bill in bills["bills"])


def test_validator_rejects_literal_digits():
    valid, reason = validate(
        "The saving is 500 rupees.", {"saving_inr": 500}, {}
    )
    assert valid is False
    assert "digit" in reason.lower()


def test_validator_rejects_unknown_placeholder():
    valid, reason = validate(
        "Saving: {{invented_inr}}.", {"saving_inr": 500}, {}
    )
    assert valid is False
    assert "Unknown placeholder" in reason


def test_validator_accepts_and_formats():
    facts = {
        "saving_inr": 12500,
        "pump_excess_kwh": 1234.4,
        "alert_yoy_pct": 12.34,
    }
    slots = {"alert_month_label": "2025-12"}
    raw = (
        "During {{text:alert_month_label}}, excess use was "
        "{{pump_excess_kwh}}, the change was {{alert_yoy_pct}}, "
        "and potential saving was {{saving_inr}}."
    )

    assert validate(raw, facts, slots) == (True, "accepted")
    text = render(raw, facts, slots)
    assert "₹12,500" in text
    assert "1,234 kWh" in text
    assert "12.3%" in text
    assert "2025-12" in text


def test_validator_rejects_long_and_malformed():
    assert validate("word " * 221, {}, {})[0] is False
    assert validate("Value {{broken-key}}", {}, {})[0] is False


def test_invalid_bedrock_twice_falls_back_and_is_stored(
    dataset, aws, monkeypatch
):
    load_dataset(dataset, aws)
    assert call(api.analysis_run)[0] == 200
    client = invalid_client()

    monkeypatch.setattr(
        api,
        "generate_summary",
        lambda result: generate_summary(result, client, "test-model"),
    )

    status, summary = call(api.summary_generate, "{}")
    assert status == 200
    assert summary["source"] == "fallback"
    assert summary["model_id"] == "test-model"
    assert summary["validator"]["outcome"] == "fallback"
    assert client.converse.call_count == 2
    assert storage.get_document("SUMMARY#latest")["source"] == "fallback"

    for request in client.converse.call_args_list:
        payload = request.kwargs
        assert payload["inferenceConfig"] == {
            "maxTokens": 700,
            "temperature": 0.2,
        }
        text = payload["messages"][0]["content"][0]["text"]
        # Retry feedback comes after the JSON payload.
        data_text = text.split("\n\nDATA:\n", 1)[1]
        data, _ = json.JSONDecoder().raw_decode(data_text)
        assert set(data) == {
            "agm_facts", "agm_facts_labels", "text_slots"
        }


def test_bedrock_exception_falls_back(dataset):
    client = Mock()
    client.converse.side_effect = TimeoutError("simulated")
    summary = generate_summary(engine.run(dataset), client, "test-model")

    assert summary["source"] == "fallback"
    assert client.converse.call_count == 1
    assert summary["validator"]["attempts"][-1]["reason"] == "bedrock_error"


def test_valid_bedrock_response(dataset):
    result = engine.run(dataset)
    inputs = make_inputs(result)
    raw = (
        "Alert period: {{text:alert_month_label}}. "
        "Reference period: {{text:reference_month_label}}. "
        "Assessment: {{text:top_hypothesis}}. "
        "Recommended actions: {{text:recommended_actions}}. "
        "These figures are estimates from synthetic data in this demo."
    )
    client = Mock()
    client.converse.return_value = {
        "output": {"message": {"content": [{"text": raw}]}},
        "stopReason": "end_turn",
    }

    summary = generate_summary(result, client, "test-model")
    assert summary["source"] == "bedrock"
    assert summary["validator"]["outcome"] == "accepted"
    assert "{{" not in summary["text"]
    assert inputs["text_slots"]["top_hypothesis"] in summary["text"]


@pytest.mark.parametrize(
    "handler",
    [api.analysis_get, api.summary_generate, api.report_create],
)
def test_missing_result_error_shape(aws, handler):
    status, body = call(handler)
    assert status == 404
    assert body["error"]["code"] == "NOT_FOUND"
    assert body["error"]["message"] == "Run POST /analysis/run first."
    assert body["error"]["request_id"] == "test-request"


@pytest.mark.parametrize("body", ["{bad", "[]", '{"apartment_id":"other"}'])
def test_bad_input_error_shape(aws, body):
    status, payload = call(api.analysis_run, body)
    assert status == 400
    assert set(payload["error"]) == {"code", "message", "request_id"}
    assert payload["error"]["code"] == "BAD_INPUT"


def test_report_written_to_private_bucket(dataset, aws, monkeypatch):
    load_dataset(dataset, aws)
    assert call(api.analysis_run)[0] == 200

    client = invalid_client()
    monkeypatch.setattr(
        api,
        "generate_summary",
        lambda result: generate_summary(result, client, "test-model"),
    )
    assert call(api.summary_generate)[0] == 200

    status, report = call(api.report_create, "{}")
    assert status == 200
    assert report["expires_in"] == 900
    assert report["key"].startswith("reports/sunrise-heights/")
    assert "X-Amz-Expires=900" in report["url"]

    s3 = boto3.client("s3", region_name="ap-south-1")
    obj = s3.get_object(Bucket=report["bucket"], Key=report["key"])
    html = obj["Body"].read().decode("utf-8")
    assert "<table>" in html
    assert "AGM summary" in html
    assert "Alerts, evidence and recommendations" in html
    assert "https://cdn" not in html

    saved = storage.get_document("REPORT#latest")
    assert saved["key"] == report["key"]
    assert "url" not in saved


def test_template_iam_is_scoped():
    class CloudFormationLoader(yaml.SafeLoader):
        pass

    def intrinsic(loader, tag, node):
        if isinstance(node, yaml.ScalarNode):
            value = loader.construct_scalar(node)
        elif isinstance(node, yaml.SequenceNode):
            value = loader.construct_sequence(node)
        else:
            value = loader.construct_mapping(node)
        return {tag: value}

    CloudFormationLoader.add_multi_constructor("!", intrinsic)

    template = yaml.load(
        (ROOT / "template.yaml").read_text(),
        Loader=CloudFormationLoader,
    )

    checked = 0
    for resource in template["Resources"].values():
        if resource["Type"] != "AWS::Serverless::Function":
            continue

        for policy in resource["Properties"].get("Policies", []):
            for statement in policy.get("Statement", []):
                actions = statement["Action"]
                actions = [actions] if isinstance(actions, str) else actions
                service_actions = [
                    action for action in actions
                    if action.startswith(("bedrock:", "dynamodb:", "s3:"))
                ]
                if not service_actions:
                    continue

                checked += 1
                resource_value = statement["Resource"]
                assert resource_value != "*"
                assert resource_value != ["*"]

                if any(action.startswith("dynamodb:") for action in actions):
                    assert resource_value == {"GetAtt": "Table.Arn"}

                if any(action.startswith("bedrock:") for action in actions):
                    assert resource_value == {"Ref": "BedrockInvokeArns"}

                if any(action.startswith("s3:") for action in actions):
                    assert resource_value == {
                        "Sub": "${ReportBucket.Arn}/reports/sunrise-heights/*"
                    }

    assert checked > 0

    pattern = template["Parameters"]["BedrockInvokeArns"]["AllowedPattern"]
    import re
    assert re.fullmatch(
        pattern,
        "arn:aws:bedrock:ap-south-1::foundation-model/vendor.model-v1",
    )
    assert not re.fullmatch(pattern, "*")
    assert not re.fullmatch(
        pattern, "arn:aws:bedrock:*::foundation-model/*"
    )