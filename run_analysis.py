#!/usr/bin/env python3
"""CLI: reads ./data and writes ./output/analysis_result.json."""
import argparse
from pathlib import Path

import engine


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Watt & Where analysis engine")
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--output", default="output/analysis_result.json")
    args = ap.parse_args(argv)
    result = engine.run(args.data_dir)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(engine.to_json(result), encoding="utf-8", newline="\n")
    statuses = {m["status"]: 0 for m in result["months"]}
    for m in result["months"]:
        statuses[m["status"]] += 1
    print(f"Wrote {out} ({len(result['months'])} months, statuses: {statuses}, alerts: {[a['month'] for a in result['alerts']]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())