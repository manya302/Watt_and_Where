from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import datetime, timezone

import boto3
from botocore.config import Config

from common.http import APIError, endpoint
from common.storage import (
    MissingData,
    apartment_id,
    get_document,
    load_engine_data,
    put_document,
    query_prefix,
)
from common.summary import generate_summary
from common.report import build_report


def result_hash(result):
    encoded = json.dumps(
        result, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def required_document(sk, instruction):
    try:
        return get_document(sk)
    except MissingData:
        raise APIError(404, "NOT_FOUND", instruction)


@endpoint
def bills(event, context):
    records = query_prefix("BILL#")
    if not records:
        raise APIError(404, "NOT_FOUND", "Load data using scripts/load_data.py first.")

    rows = sorted(
        (item["payload"] for item in records),
        key=lambda row: row["month"],
    )
    return {
        "apartment_id": apartment_id(),
        "bills": [
            {
                "month": row["month"],
                "total_units_kwh": row["total_units_kwh"],
                "total_amount": row["total_amount"],
            }
            for row in rows
        ],
    }


@endpoint
def analysis_run(event, context):
    from common.engine import analyze

    data = load_engine_data()
    try:
        result = analyze(data)
    except (ValueError, KeyError, TypeError, IndexError, ZeroDivisionError):
        raise APIError(
            422,
            "INVALID_DATA",
            "Stored input data cannot be analyzed. Regenerate and reload the dataset.",
        )

    put_document("RESULT#latest", result)
    return result


@endpoint
def analysis_get(event, context):
    return required_document("RESULT#latest", "Run POST /analysis/run first.")


@endpoint
def summary_generate(event, context):
    result = required_document("RESULT#latest", "Run POST /analysis/run first.")
    summary = generate_summary(result)
    summary["result_hash"] = result_hash(result)
    put_document("SUMMARY#latest", summary)
    return summary


@endpoint
def summary_get(event, context):
    return required_document(
        "SUMMARY#latest", "Run POST /summary/generate first."
    )


@endpoint
def report_create(event, context):
    result = required_document("RESULT#latest", "Run POST /analysis/run first.")
    summary = required_document(
        "SUMMARY#latest", "Run POST /summary/generate first."
    )

    if summary.get("result_hash") != result_hash(result):
        raise APIError(
            409,
            "STALE_SUMMARY",
            "Analysis changed. Run POST /summary/generate again.",
        )

    bucket = os.environ["REPORT_BUCKET"]
    key = f"reports/{apartment_id()}/{uuid.uuid4().hex}.html"

    region = os.environ.get("AWS_REGION", "ap-south-1")

    s3 = boto3.client(
        "s3",
        region_name=region,
        endpoint_url=f"https://s3.{region}.amazonaws.com",
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "virtual"},
            connect_timeout=2,
            read_timeout=5,
            retries={"mode": "standard", "total_max_attempts": 2},
        ),
    )
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=build_report(result, summary).encode("utf-8"),
        ContentType="text/html; charset=utf-8",
        ServerSideEncryption="AES256",
    )

    url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=900,
    )

    metadata = {
        "bucket": bucket,
        "key": key,
        "expires_in": 900,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "result_hash": result_hash(result),
    }
    put_document("REPORT#latest", metadata)

    return {**metadata, "url": url}