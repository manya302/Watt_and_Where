#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.common.engine import load_data
from src.common.storage import table, to_ddb


def load_dataset(data_dir="data", db=None, apartment="sunrise-heights"):
    db = db if db is not None else table()
    data = load_data(data_dir)
    items = []

    def add(sk, payload, order=0):
        items.append(to_ddb({
            "apartment_id": apartment,
            "SK": sk,
            "row_order": order,
            "payload": payload,
        }))

    for index, row in enumerate(data["bills"].to_dict("records")):
        add(f"BILL#{row['month']}", row, index)

    for index, row in enumerate(data["inventory"].to_dict("records")):
        add(f"EQUIP#{row['equipment_id']}", row, index)

    cycles = defaultdict(int)
    for index, row in enumerate(data["pump_log"].to_dict("records")):
        group = (row["date"], row["pump_id"])
        cycles[group] += 1
        add(
            f"PUMPLOG#{group[0]}#{group[1]}#{cycles[group]:04d}",
            row,
            index,
        )

    events = defaultdict(int)
    for index, row in enumerate(data["dg_log"].to_dict("records")):
        events[row["date"]] += 1
        add(f"DG#{row['date']}#{events[row['date']]:04d}", row, index)

    add("TARIFF#current", data["tariff"])

    keys = [(item["apartment_id"], item["SK"]) for item in items]
    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate source identifiers in dataset")

    with db.batch_writer(overwrite_by_pkeys=["apartment_id", "SK"]) as batch:
        for item in items:
            batch.put_item(Item=item)

    return len(items)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="data")
    args = parser.parse_args()
    count = load_dataset(args.data_dir)
    print(f"Loaded {count} items into WattWhere.")


if __name__ == "__main__":
    main()