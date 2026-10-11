from __future__ import annotations

import math
import os
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key
from botocore.config import Config


AWS_CONFIG = Config(
    connect_timeout=2,
    read_timeout=5,
    retries={"mode": "standard", "total_max_attempts": 2},
)


class MissingData(Exception):
    pass


def apartment_id():
    return os.environ.get("APARTMENT_ID", "sunrise-heights")


def table():
    return boto3.resource(
        "dynamodb",
        region_name=os.environ.get("AWS_REGION", "ap-south-1"),
        config=AWS_CONFIG,
    ).Table(os.environ.get("TABLE_NAME", "WattWhere"))


def to_ddb(value):
    """Convert JSON-compatible values into DynamoDB-safe values."""
    if isinstance(value, dict):
        return {str(k): to_ddb(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_ddb(v) for v in value]
    if isinstance(value, float):
        return Decimal(str(value)) if math.isfinite(value) else None
    return value


def from_ddb(value):
    if isinstance(value, dict):
        return {k: from_ddb(v) for k, v in value.items()}
    if isinstance(value, list):
        return [from_ddb(v) for v in value]
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    return value


def query_prefix(prefix, db=None, apartment=None):
    db = db if db is not None else table()
    apartment = apartment or apartment_id()

    request = {
        "KeyConditionExpression": (
            Key("apartment_id").eq(apartment) & Key("SK").begins_with(prefix)
        ),
        "ConsistentRead": True,
    }

    items = []
    while True:
        response = db.query(**request)
        items.extend(from_ddb(response.get("Items", [])))
        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            break
        request["ExclusiveStartKey"] = last_key

    return items


def get_document(sk, db=None, apartment=None):
    db = db if db is not None else table()
    response = db.get_item(
        Key={
            "apartment_id": apartment or apartment_id(),
            "SK": sk,
        },
        ConsistentRead=True,
    )
    item = response.get("Item")
    if item is None:
        raise MissingData(f"{sk} does not exist")
    return from_ddb(item["payload"])


def put_document(sk, payload, db=None, apartment=None):
    db = db if db is not None else table()
    db.put_item(
        Item=to_ddb({
            "apartment_id": apartment or apartment_id(),
            "SK": sk,
            "payload": payload,
        })
    )


def load_engine_data(db=None, apartment=None):
    # Only the analysis Lambda imports pandas.
    import pandas as pd

    db = db if db is not None else table()
    apartment = apartment or apartment_id()

    def records(prefix):
        items = query_prefix(prefix, db, apartment)
        items.sort(key=lambda item: item.get("row_order", 0))
        return [item["payload"] for item in items]

    bills = records("BILL#")
    inventory = records("EQUIP#")
    pump_log = records("PUMPLOG#")
    dg_log = records("DG#")

    if not bills or not inventory:
        raise MissingData("Load bills and equipment using scripts/load_data.py")

    return {
        "bills": pd.DataFrame(bills),
        "inventory": pd.DataFrame(inventory),
        "pump_log": pd.DataFrame(pump_log) if pump_log else pd.DataFrame(columns=[
            "date", "pump_id", "start_time", "stop_time", "runtime_min",
            "tank_level_start_pct", "tank_level_stop_pct",
            "pressure_switch_status",
        ]),
        "dg_log": pd.DataFrame(dg_log) if dg_log else pd.DataFrame(columns=[
            "date", "run_hours", "cost_inr",
        ]),
        "tariff": get_document("TARIFF#current", db, apartment),
    }